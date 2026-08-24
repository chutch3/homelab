"""The stack dependency graph declared by ``x-homelab: {requires: [...]}``.

Deploy order was the output of ``find``. It is now a topological sort of the
declarations. :func:`resolve` and :func:`inferred_requires` are pure and
unit-tested; reading the tree is glue.

Nothing here deploys — it only decides what order a deploy would use.
"""

from __future__ import annotations

import os
import re
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


class UnresolvedGraph(Exception):
    """The declarations do not describe a deployable order."""


def declared_requires(compose: dict) -> list[str]:
    """The ``x-homelab.requires`` list, or empty when the stack declares none."""
    return list((compose.get("x-homelab") or {}).get("requires") or [])


def inferred_requires(stack: str, compose_text: str) -> set[str]:
    """Dependencies the compose file itself reveals, whatever it declares."""
    return {p for p, pattern in _INFERENCE if pattern.search(compose_text)} - {stack}


def compose_paths(repo_root: str | Path) -> dict[str, Path]:
    """Stack name -> its docker-compose.yml, across both stack roots."""
    root = Path(repo_root)
    return {
        path.parent.name: path
        for stack_root in STACK_ROOTS
        for path in sorted((root / stack_root).glob("*/docker-compose.yml"))
    }


def load_graph(repo_root: str | Path) -> dict[str, list[str]]:
    """Stack name -> declared requires, read from the tree."""
    return {
        name: declared_requires(yaml.safe_load(path.read_text()) or {})
        for name, path in compose_paths(repo_root).items()
    }


def undeclared(repo_root: str | Path, paths: list[str] | None = None) -> dict[str, set[str]]:
    """Stacks whose compose reveals a dependency they do not declare.

    ``paths`` narrows the scan to those compose files, so pre-commit can scope
    the check to a diff and carry its baseline as an ordinary ``exclude:``.
    """
    only = {Path(p).resolve() for p in paths} if paths is not None else None
    found = {}
    for name, path in compose_paths(repo_root).items():
        if only is not None and path.resolve() not in only:
            continue
        text = path.read_text()
        missing = inferred_requires(name, text) - set(declared_requires(yaml.safe_load(text) or {}))
        if missing:
            found[name] = missing
    return found


def disabled_by_capability(env: dict[str, str] | None = None) -> set[str]:
    """Provider stacks this environment has switched off."""
    env = os.environ if env is None else env
    return {
        stack
        for stack, var in CAPABILITY_GATES.items()
        if env.get(var, "true").strip().lower() in ("false", "no", "0", "")
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
