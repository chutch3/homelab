"""What the Swarm cluster currently holds, so a plan can say what will change.

Two list commands answer it: `docker stack ls` names what exists, `docker
service ls` gives each service its `running/desired` column. Nothing here
writes — a plan that mutated the thing it is describing would be a lie.

Converged means desired replicas *and* no update in flight; the reasoning for
both halves is in docs/architecture/overview.md, "What converged means".
"""

from __future__ import annotations

import re
from collections import defaultdict
from enum import Enum

from ci.ports import CommandRunner

STACK_LS = ["docker", "stack", "ls", "--format", "{{.Name}}"]
SERVICE_LS = ["docker", "service", "ls", "--format", "{{.Name}}\t{{.Replicas}}"]
# `service ls` cannot report UpdateStatus, so every service is inspected at once.
UPDATE_FORMAT = "{{.Spec.Name}}\t{{if .UpdateStatus}}{{.UpdateStatus.State}}{{else}}none{{end}}"
SERVICE_INSPECT = ["docker", "service", "inspect", "--format", UPDATE_FORMAT]

# Still moving, or stopped needing a human. Anything else is settled.
UNSETTLED = frozenset({"updating", "paused", "rollback_started"})

# Swarm's replicas column: `1/1`, or `1/1 (max 1 per node)` under a placement limit.
REPLICAS = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


class ClusterUnreachable(Exception):
    """The cluster could not be read, so no state can be reported."""


class StackState(Enum):
    ABSENT = "absent"
    PRESENT = "present"
    CONVERGED = "converged"


def parse_replicas(column: str) -> tuple[int, int]:
    """Running and desired replicas. Anything unreadable is never converged."""
    if match := REPLICAS.match(column):
        return int(match.group(1)), int(match.group(2))
    return -1, 0


class SwarmCluster:
    """The live state of every stack, read once per invocation."""

    def __init__(self, commands: CommandRunner) -> None:
        self._commands = commands
        self._states: dict[str, StackState] | None = None

    def state(self, stack: str) -> StackState:
        return self.states().get(stack, StackState.ABSENT)

    def states(self) -> dict[str, StackState]:
        if self._states is None:
            self._states = self._read()
        return self._states

    def _read(self) -> dict[str, StackState]:
        deployed = self._lines(STACK_LS)
        services = [line.partition("\t") for line in self._lines(SERVICE_LS)]
        updates = self._updates([name for name, _, _ in services])
        replicas: dict[str, list[tuple[int, int]]] = defaultdict(list)
        settled: dict[str, bool] = defaultdict(lambda: True)
        for name, _, column in services:
            if owner := _owner(name, deployed):
                replicas[owner].append(parse_replicas(column))
                settled[owner] &= updates.get(name, "none") not in UNSETTLED
        return {
            stack: StackState.CONVERGED
            if replicas[stack]
            and all(run == want for run, want in replicas[stack])
            and settled[stack]
            else StackState.PRESENT
            for stack in deployed
        }

    def _updates(self, services: list[str]) -> dict[str, str]:
        """Service name -> its update state, or `none` where it has never updated."""
        if not services:
            return {}
        return dict(
            (name, state)
            for name, _, state in (
                line.partition("\t") for line in self._lines(SERVICE_INSPECT + services)
            )
        )

    def _lines(self, argv: list[str]) -> list[str]:
        outcome = self._commands.run(argv, capture=True)
        if not outcome.ok:
            raise ClusterUnreachable(f"{' '.join(argv[:3])} failed: {outcome.stderr.strip()}")
        return [line for line in outcome.stdout.splitlines() if line.strip()]


def _owner(service: str, stacks: list[str]) -> str | None:
    """The stack a service belongs to: the longest name it is prefixed with.

    Stack names contain underscores (`actual_server`), so the prefix is only
    unambiguous against the set the cluster actually reports.
    """
    candidates = [s for s in stacks if service.startswith(f"{s}_")]
    return max(candidates, key=len) if candidates else None
