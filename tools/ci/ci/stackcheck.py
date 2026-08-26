"""The invariants every stack in the tree must hold — the `ci check-stacks` verdict.

Two rules today: the ``x-homelab`` declarations resolve and are complete, and
every stack declares a healthcheck. They share a command because they share a
question — is this tree deployable — and a tree read once answers both.

Convergence is what makes the second rule matter: the deploy waits for each
stack to converge before starting the next, and Swarm calls a task ``running``
the moment its process starts unless a healthcheck says otherwise. See
docs/architecture/overview.md, "What converged means".

:func:`parse_ratchet` is pure — the composition root does the file read.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from ci.ports import FileSystem
from ci.stackgraph import DependencyGraph, Stack, StackTree, UnresolvedGraph

log = logging.getLogger(__name__)

# Where the baseline lives: data, beside the `exclude:` ratchets in
# .pre-commit-config.yaml that it mirrors, rather than a literal in this module.
RATCHET_FILE = ".stack-checks.yml"


def parse_ratchet(text: str) -> frozenset[str]:
    """The stacks exempt from the healthcheck rule. Absent or empty means none."""
    document = yaml.safe_load(text) or {}
    names = document.get("without_healthcheck") or []
    if not isinstance(names, list) or any(not isinstance(n, str) for n in names):
        raise ValueError(f"{RATCHET_FILE}: without_healthcheck must be a list of stack names")
    return frozenset(names)


def load_ratchet(filesystem: FileSystem, repo_root: str | Path = ".") -> frozenset[str]:
    path = Path(repo_root) / RATCHET_FILE
    return parse_ratchet(filesystem.read_text(path) if filesystem.exists(path) else "")


def check_stacks(
    tree: StackTree, graph: DependencyGraph, without_healthcheck: frozenset[str]
) -> int:
    """Every invariant, over one read of the tree. Non-zero names what failed."""
    try:
        stacks = tree.stacks()
        graph.resolve()
    except UnresolvedGraph as exc:
        log.error("✗ %s", exc)
        return 1

    if _report_undeclared(graph) | _report_bare(stacks, without_healthcheck):
        return 1
    log.info("✓ %d stacks resolve, declare what they need, and say when they are ready", len(stacks))
    return 0


def _report_undeclared(graph: DependencyGraph) -> bool:
    if not (missing := graph.undeclared()):
        return False
    log.error("✗ dependencies visible in the compose file but not declared in x-homelab.requires:")
    for stack, requires in sorted(missing.items()):
        log.error("    %s: %s", stack, ", ".join(sorted(requires)))
    return True


def _report_bare(stacks: dict[str, Stack], exempt: frozenset[str]) -> bool:
    bare = sorted(n for n, s in stacks.items() if not s.has_healthcheck and n not in exempt)
    if not bare:
        return False
    log.error("✗ stacks with no healthcheck — the deploy cannot tell when they are ready:")
    for name in bare:
        log.error("    %s", name)
    return True
