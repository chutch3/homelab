"""The deploy plan: resolved order, live state, and why each stack is in it.

`ci deploy --plan` exists to show what a deploy *would change*, not to list the
whole tree. That takes two things this module joins — the order the
declarations imply (:mod:`ci.stackgraph`) and what the cluster already holds
(:mod:`ci.cluster`).

Nothing here deploys. The verbs are how a row got into the plan: `deploy` for a
stack that was named, `ensure` for one pulled in behind it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from ci.cluster import ClusterUnreachable, StackState, SwarmCluster
from ci.stackgraph import DependencyGraph, UnresolvedGraph

log = logging.getLogger(__name__)


class Origin(Enum):
    """How a stack got into the plan."""

    TARGET = "target"  # named on the command line
    DEPENDENCY = "dependency"  # pulled in behind a target
    WHOLE_TREE = "whole-tree"  # no targets named, so the plan is everything

    @property
    def verb(self) -> str:
        return "ensure" if self is Origin.DEPENDENCY else "deploy"


@dataclass(frozen=True)
class PlanRow:
    """One stack in the plan: how it got there, and what it is right now.

    Holds no display text. `required_by` is the stacks themselves, so a caller
    can act on them; turning that into a column is :func:`_render`'s job.
    """

    stack: str
    state: StackState
    origin: Origin
    required_by: tuple[str, ...] = ()


class DeployPlan:
    def __init__(self, graph: DependencyGraph, cluster: SwarmCluster) -> None:
        self._graph = graph
        self._cluster = cluster

    def rows(self, targets: list[str] | None = None) -> list[PlanRow]:
        order = self._graph.resolve(targets)
        # A full plan has no target to attribute anything to: everything in it
        # was asked for.
        pulled_in = self._graph.required_by(targets) if targets else {}
        named = set(targets or ())
        rows = []
        for stack in order:
            requiring: tuple[str, ...] = ()
            if not targets:
                origin = Origin.WHOLE_TREE
            elif stack in named:
                origin = Origin.TARGET
            else:
                origin = Origin.DEPENDENCY
                requiring = tuple(pulled_in.get(stack, []))
            rows.append(PlanRow(stack, self._cluster.state(stack), origin, requiring))
        return rows

    def report(self, targets: list[str] | None = None) -> int:
        """Print the plan. Reads the cluster, changes nothing, exits 1 on failure."""
        try:
            rows = self.rows(targets)
        except (UnresolvedGraph, ClusterUnreachable) as exc:
            log.error("✗ %s", exc)
            return 1
        for line in _render(rows):
            print(line)
        log.info("%d stack(s) — plan only, nothing deployed.", len(rows))
        return 0


def _reason(row: PlanRow) -> str:
    """Why the row is in the plan, as the column reads it."""
    if row.origin is Origin.DEPENDENCY:
        return f"required by {', '.join(row.required_by)}"
    if row.origin is Origin.TARGET:
        return "explicit target"
    return ""


def _render(rows: list[PlanRow]) -> list[str]:
    """Aligned columns, so the states can be scanned down rather than read."""
    verb = max((len(r.origin.verb) for r in rows), default=0)
    stack = max((len(r.stack) for r in rows), default=0)
    state = max((len(r.state.value) for r in rows), default=0)
    return [
        f"  {r.origin.verb:<{verb}}   {r.stack:<{stack}}   {r.state.value:<{state}}"
        + (f"   → {reason}" if (reason := _reason(r)) else "")
        for r in rows
    ]
