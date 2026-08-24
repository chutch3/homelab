"""The stack dependency graph declared by ``x-homelab: {requires: [...]}``.

Deploy order was the output of ``find``. It is now a topological sort of the
declarations. :func:`resolve` and :func:`inferred_requires` are pure and
unit-tested; reading the tree is glue.

Nothing here deploys — it only decides what order a deploy would use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

# Stacks live one directory deep in each of these, alongside a docker-compose.yml.
STACK_ROOTS = ("stacks", "stacks/apps")

# Edges a compose file gives away on its own, so a missing declaration is a
# check failure rather than a surprise at deploy time. Text patterns, not
# parsed YAML: the labels these match are free-form strings either way.
_INFERENCE = (
    ("reverse-proxy", re.compile(r"traefik\.enable=true")),
    ("authentik", re.compile(r"middlewares=[^\"]*authentik@|auth\.\$\{BASE_DOMAIN\}")),
)

# Providers the cluster can be configured without. Deploy already skips the dns
# stack on primary_dns_managed (ansible/playbooks/deploy/stacks.yml); the graph
# has to drop the edges into it too, or every routed stack becomes unresolvable.
CAPABILITY_GATES = {"dns": "PRIMARY_DNS_MANAGED"}

_FALSEY = ("false", "no", "0", "")
_DOTENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


class UnresolvedGraph(Exception):
    """The declarations do not describe a deployable order."""


@dataclass(frozen=True)
class Stack:
    """One stack, read once: its compose text and what it declares."""

    name: str
    path: Path
    text: str
    requires: tuple[str, ...]

    @property
    def undeclared(self) -> set[str]:
        """Dependencies its compose reveals but it does not declare."""
        return inferred_requires(self.name, self.text) - set(self.requires)


def inferred_requires(stack: str, compose_text: str) -> set[str]:
    """Dependencies the compose file itself reveals, whatever it declares."""
    return {p for p, pattern in _INFERENCE if pattern.search(compose_text)} - {stack}


def _declared(name: str, compose_text: str) -> tuple[str, ...]:
    """The validated ``x-homelab.requires``, or empty when none is declared.

    The shape is also enforced by schemas/stack-manifest.schema.json at commit
    time; repeating it here keeps a hand-run check from resolving garbage.
    """
    try:
        document = yaml.safe_load(compose_text) or {}
    except yaml.YAMLError as exc:
        raise UnresolvedGraph(f"{name}: compose file is not valid YAML: {exc}") from exc
    if not isinstance(document, dict):
        raise UnresolvedGraph(f"{name}: compose file is not a mapping")

    manifest = document.get("x-homelab")
    if manifest is None:
        return ()
    if not isinstance(manifest, dict):
        raise UnresolvedGraph(f"{name}: x-homelab must be a mapping, got {type(manifest).__name__}")

    requires = manifest.get("requires", [])
    if not isinstance(requires, list):
        raise UnresolvedGraph(
            f"{name}: x-homelab.requires must be a list of stack names, "
            f"got {type(requires).__name__}"
        )
    if bad := [r for r in requires if not isinstance(r, str)]:
        raise UnresolvedGraph(f"{name}: x-homelab.requires entries must be stack names: {bad}")
    return tuple(requires)


def load_stacks(repo_root: str | Path) -> dict[str, Stack]:
    """Every stack in the tree, name -> :class:`Stack`, each file read once."""
    root = Path(repo_root)
    stacks: dict[str, Stack] = {}
    for stack_root in STACK_ROOTS:
        for path in sorted((root / stack_root).glob("*/docker-compose.yml")):
            name = path.parent.name
            if name in stacks:
                raise UnresolvedGraph(f"two stacks named {name}: {stacks[name].path} and {path}")
            text = path.read_text()
            stacks[name] = Stack(name, path, text, _declared(name, text))
    return stacks


def load_graph(repo_root: str | Path) -> dict[str, list[str]]:
    """Stack name -> declared requires, read from the tree."""
    return {name: list(stack.requires) for name, stack in load_stacks(repo_root).items()}


def undeclared(repo_root: str | Path) -> dict[str, set[str]]:
    """Stacks whose compose reveals a dependency they do not declare."""
    found = {n: s.undeclared for n, s in load_stacks(repo_root).items()}
    return {name: missing for name, missing in found.items() if missing}


def environment(repo_root: str | Path, process_env: dict[str, str]) -> dict[str, str]:
    """``.env`` overlaid with the process environment, which wins.

    `task deploy:plan` is handed .env by the Taskfile's ``dotenv:``; running the
    CLI directly is not, and the two must not disagree about what is switched on.
    """
    merged: dict[str, str] = {}
    dotenv = Path(repo_root) / ".env"
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            if line.lstrip().startswith("#") or not (match := _DOTENV_LINE.match(line)):
                continue
            key, value = match.groups()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            merged[key] = value
    merged.update(process_env)
    return merged


def disabled_by_capability(env: dict[str, str]) -> set[str]:
    """Provider stacks this environment has switched off."""
    return {
        stack
        for stack, var in CAPABILITY_GATES.items()
        if env.get(var, "true").strip().lower() in _FALSEY
    }


def _cycle(edges: dict[str, list[str]], stuck: list[str]) -> list[str]:
    """The stacks actually in a cycle, dropping those merely blocked behind one."""
    members = set(stuck)
    while shed := {s for s in members if not any(s in edges[o] for o in members)}:
        members -= shed
    return sorted(members)


def resolve(
    graph: dict[str, list[str]],
    targets: list[str] | None = None,
    disabled: list[str] | None = None,
) -> list[str]:
    """Deploy order: every stack after all of its dependencies.

    ``targets`` narrows the result to those stacks and what they need.
    ``disabled`` names providers this environment does without — they are
    dropped, and so are the edges into them, rather than failing to resolve.
    """
    off = set(disabled or ())
    edges = {
        stack: sorted(set(requires) - off)
        for stack, requires in graph.items()
        if stack not in off
    }

    if unknown := {(s, d) for s, ds in edges.items() for d in ds if d not in edges}:
        detail = ", ".join(f"{s} requires {d}" for s, d in sorted(unknown))
        raise UnresolvedGraph(f"dependency on a stack that does not exist: {detail}")

    wanted = set(edges)
    if targets is not None:
        if missing := sorted(set(targets) - set(graph)):
            raise UnresolvedGraph(f"no such stack: {', '.join(missing)}")
        wanted, frontier = set(), [t for t in targets if t not in off]
        while frontier:
            if (stack := frontier.pop()) not in wanted:
                wanted.add(stack)
                frontier.extend(edges[stack])

    order, placed = [], set()
    # Alphabetical among stacks whose dependencies are all placed, so the same
    # graph always yields the same order.
    while remaining := sorted(wanted - placed):
        ready = [s for s in remaining if not set(edges[s]) - placed]
        if not ready:
            raise UnresolvedGraph(f"dependency cycle among: {', '.join(_cycle(edges, remaining))}")
        order.extend(ready)
        placed.update(ready)
    return order
