"""The deploy plan: resolved order, live state, and what each row will do.

`ci plan` exists to show what a deploy *would change*, not to list the whole
tree. That takes two things this module joins — the order the declarations
imply (:mod:`ci.stackgraph`) and what the cluster already holds
(:mod:`ci.docker`, read as state by :mod:`ci.stackstate`).

Nothing here deploys. It decides, and `ansible/playbooks/deploy/stacks.yml`
loops over the answer it prints with ``--json``. Only a stack you named is
deployed unconditionally; anything else is a means to that end, and a means
that has already converged is left alone.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum

from ci.docker import ClusterUnreachable, Docker
from ci.stackgraph import DependencyGraph, UnresolvedGraph
from ci.stackstate import StackState, stack_states

log = logging.getLogger(__name__)


class Origin(Enum):
    """How a stack got into the plan — the cause, never the action."""

    TARGET = "target"  # named on the command line
    DEPENDENCY = "dependency"  # pulled in behind a target
    WHOLE_TREE = "whole-tree"  # no targets named, so the plan is everything


class Action(Enum):
    """What the run will do with a row."""

    DEPLOY = "deploy"
    SKIP = "skip"


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

    @property
    def action(self) -> Action:
        """Deploy, unless this stack was not named and has already converged."""
        if self.origin is not Origin.TARGET and self.state is StackState.CONVERGED:
            return Action.SKIP
        return Action.DEPLOY


class DeployPlanner:
    def __init__(self, graph: DependencyGraph, docker: Docker) -> None:
        self._graph = graph
        self._docker = docker

    def rows(self, targets: list[str] | None = None) -> list[PlanRow]:
        order = self._graph.resolve(targets)
        states = stack_states(self._docker.services())
        # A full plan has no target to attribute anything to: nothing in it was
        # named, so nothing in it is redeployed for having been asked for.
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
            state = states.get(stack, StackState.ABSENT)
            rows.append(PlanRow(stack, state, origin, requiring))
        return rows

    def report(self, targets: list[str] | None = None, as_json: bool = False) -> int:
        """Print the plan. Reads the cluster, changes nothing, exits 1 on failure."""
        try:
            rows = self.rows(targets)
        except (UnresolvedGraph, ClusterUnreachable) as exc:
            log.error("✗ %s", exc)
            return 1
        if dropped := sorted(set(targets or ()) & self._graph.disabled()):
            log.error(
                "✗ named but switched off in this environment, so nothing was planned "
                "for %s — check its capability gate before deploying it",
                ", ".join(dropped),
            )
            return 1
        if as_json:
            print(json.dumps([_as_dict(r) for r in rows]))
        else:
            for line in _render(rows):
                print(line)
        log.info(
            "%d stack(s), %d to deploy — plan only, nothing deployed.",
            len(rows),
            sum(r.action is Action.DEPLOY for r in rows),
        )
        return 0


def _as_dict(row: PlanRow) -> dict[str, str]:
    """The row as the playbook reads it: what to do, to which stack, and from what."""
    return {"stack": row.stack, "state": row.state.value, "action": row.action.value}


def _reason(row: PlanRow) -> str:
    """Why the row is in the plan, as the column reads it."""
    if row.origin is Origin.DEPENDENCY:
        return f"required by {', '.join(row.required_by)}"
    if row.origin is Origin.TARGET:
        return "explicit target"
    return ""


def _render(rows: list[PlanRow]) -> list[str]:
    """Aligned columns, so the actions can be scanned down rather than read."""
    action = max((len(r.action.value) for r in rows), default=0)
    stack = max((len(r.stack) for r in rows), default=0)
    state = max((len(r.state.value) for r in rows), default=0)
    return [
        f"  {r.action.value:<{action}}   {r.stack:<{stack}}   {r.state.value:<{state}}"
        + (f"   → {reason}" if (reason := _reason(r)) else "")
        for r in rows
    ]
