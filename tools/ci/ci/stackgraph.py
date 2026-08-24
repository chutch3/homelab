"""The stack dependency graph declared by ``x-homelab: {requires: [...]}``.

Deploy order was the output of ``find``. It is now a topological sort of the
declarations. :class:`StackTree` owns the filesystem; :class:`DependencyGraph`
holds the logic and takes the tree, so its tests never touch disk.

Nothing here deploys — it only decides what order a deploy would use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from ci.config import disabled_providers
from ci.ports import FileSystem

# Stacks live one directory deep in each of these, alongside a docker-compose.yml.
STACK_ROOTS = ("stacks", "stacks/apps")

# Edges a compose file gives away on its own, so a missing declaration is a
# check failure rather than a surprise at deploy time. Text patterns, not
# parsed YAML: the labels these match are free-form strings either way.
INFERENCE = (
    ("reverse-proxy", re.compile(r"traefik\.enable=true")),
    ("authentik", re.compile(r"middlewares=[^\"]*authentik@|auth\.\$\{BASE_DOMAIN\}")),
)



class UnresolvedGraph(Exception):
    """The declarations do not describe a deployable order."""


@dataclass(frozen=True)
class Stack:
    """One stack: its compose text and the dependencies it declares."""

    name: str
    path: Path
    text: str
    requires: tuple[str, ...]

    @property
    def inferred(self) -> set[str]:
        """Dependencies the compose file reveals, whatever it declares."""
        return {p for p, pattern in INFERENCE if pattern.search(self.text)} - {self.name}

    @property
    def undeclared(self) -> set[str]:
        """Dependencies its compose reveals but it does not declare."""
        return self.inferred - set(self.requires)


class StackTree:
    """Reads the stacks out of the working tree, each compose file parsed once."""

    def __init__(self, filesystem: FileSystem, repo_root: str | Path = ".") -> None:
        self._fs = filesystem
        self._root = Path(repo_root)

    def stacks(self) -> dict[str, Stack]:
        stacks: dict[str, Stack] = {}
        for stack_root in STACK_ROOTS:
            for path in self._fs.glob(self._root / stack_root, "*/docker-compose.yml"):
                name = path.parent.name
                if name in stacks:
                    raise UnresolvedGraph(
                        f"two stacks named {name}: {stacks[name].path} and {path}"
                    )
                text = self._fs.read_text(path)
                stacks[name] = Stack(name, path, text, self._declared(name, text))
        return stacks

    def _declared(self, name: str, compose_text: str) -> tuple[str, ...]:
        """The validated ``x-homelab.requires``, or empty when none is declared.

        The shape is also enforced by schemas/stack-manifest.schema.json at
        commit time; repeating it keeps a hand-run check from resolving garbage.
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
            raise UnresolvedGraph(
                f"{name}: x-homelab must be a mapping, got {type(manifest).__name__}"
            )
        requires = manifest.get("requires", [])
        if not isinstance(requires, list):
            raise UnresolvedGraph(
                f"{name}: x-homelab.requires must be a list of stack names, "
                f"got {type(requires).__name__}"
            )
        if bad := [r for r in requires if not isinstance(r, str)]:
            raise UnresolvedGraph(f"{name}: x-homelab.requires entries must be stack names: {bad}")
        return tuple(requires)


class DependencyGraph:
    """Deploy order over the declarations, and what the declarations are missing."""

    def __init__(
        self,
        tree: StackTree,
        env: dict[str, str] | None = None,
        gates: dict[str, str] | None = None,
    ) -> None:
        self._tree = tree
        self._env = env or {}
        self._gates = gates

    def stacks(self) -> dict[str, Stack]:
        return self._tree.stacks()

    def edges(self) -> dict[str, list[str]]:
        """Stack name -> declared requires."""
        return {name: list(stack.requires) for name, stack in self.stacks().items()}

    def undeclared(self) -> dict[str, set[str]]:
        """Stacks whose compose reveals a dependency they do not declare."""
        return {n: s.undeclared for n, s in self.stacks().items() if s.undeclared}

    def disabled(self) -> set[str]:
        """Provider stacks this environment has switched off."""
        return disabled_providers(self._env, self._gates)

    def resolve(self, targets: list[str] | None = None) -> list[str]:
        """Deploy order: every stack after all of its dependencies."""
        return resolve(self.edges(), targets, sorted(self.disabled()))

    def required_by(self, targets: list[str]) -> dict[str, list[str]]:
        """For each stack a target pulls in, the targets that reach it."""
        return required_by(self.edges(), targets, sorted(self.disabled()))


def required_by(
    graph: dict[str, list[str]],
    targets: list[str],
    disabled: list[str] | None = None,
) -> dict[str, list[str]]:
    """Stack -> the named targets that reach it, transitively, over the declarations.

    A target never appears as its own dependency: `deploy paperless` reports
    reverse-proxy as required by paperless even though authentik sits between
    them, because paperless is the thing that was asked for.
    """
    off = set(disabled or ())
    edges = {s: set(r) - off for s, r in graph.items() if s not in off}
    reached: dict[str, set[str]] = {}
    for target in targets:
        if target in off:
            continue
        seen: set[str] = set()
        frontier = list(edges.get(target, ()))
        while frontier:
            if (stack := frontier.pop()) not in seen:
                seen.add(stack)
                frontier.extend(edges.get(stack, ()))
        for stack in seen:
            reached.setdefault(stack, set()).add(target)
    return {stack: sorted(ts) for stack, ts in reached.items()}


def cycle_members(edges: dict[str, list[str]], stuck: list[str]) -> list[str]:
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
    """Deploy order over a plain {stack: requires} mapping.

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

    order: list[str] = []
    placed: set[str] = set()
    # Alphabetical among stacks whose dependencies are all placed, so the same
    # graph always yields the same order.
    while remaining := sorted(wanted - placed):
        ready = [s for s in remaining if not set(edges[s]) - placed]
        if not ready:
            raise UnresolvedGraph(f"dependency cycle among: {', '.join(cycle_members(edges, remaining))}")
        order.extend(ready)
        placed.update(ready)
    return order
