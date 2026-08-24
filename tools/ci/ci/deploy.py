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

from ci.cluster import ClusterUnreachable, StackState, SwarmCluster
from ci.stackgraph import DependencyGraph, UnresolvedGraph

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlanRow:
    """One stack in the plan: how it got there, and what it is right now."""

    verb: str
    stack: str
    state: StackState
    reason: str


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
            if not targets:
                verb, reason = "deploy", ""
            elif stack in named:
                verb, reason = "deploy", "explicit target"
            else:
                verb = "ensure"
                reason = f"required by {', '.join(pulled_in.get(stack, []))}"
            rows.append(PlanRow(verb, stack, self._cluster.state(stack), reason))
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


def _render(rows: list[PlanRow]) -> list[str]:
    """Aligned columns, so the states can be scanned down rather than read."""
    verb = max((len(r.verb) for r in rows), default=0)
    stack = max((len(r.stack) for r in rows), default=0)
    state = max((len(r.state.value) for r in rows), default=0)
    return [
        f"  {r.verb:<{verb}}   {r.stack:<{stack}}   {r.state.value:<{state}}"
        + (f"   → {r.reason}" if r.reason else "")
        for r in rows
    ]
