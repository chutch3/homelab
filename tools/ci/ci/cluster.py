"""What the Swarm cluster currently holds, so a plan can say what will change.

Two list commands answer it: `docker stack ls` names what exists, `docker
service ls` gives each service its `running/desired` column. Nothing here
writes — a plan that mutated the thing it is describing would be a lie.

There is deliberately no readiness state. Swarm promotes a task to `running`
only once its healthcheck passes, so convergence *is* health.
"""

from __future__ import annotations

import re
from collections import defaultdict
from enum import Enum

from ci.ports import CommandRunner

STACK_LS = ["docker", "stack", "ls", "--format", "{{.Name}}"]
SERVICE_LS = ["docker", "service", "ls", "--format", "{{.Name}}\t{{.Replicas}}"]

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
        replicas: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for line in self._lines(SERVICE_LS):
            name, _, column = line.partition("\t")
            if owner := _owner(name, deployed):
                replicas[owner].append(parse_replicas(column))
        return {
            stack: StackState.CONVERGED
            if replicas[stack] and all(run == want for run, want in replicas[stack])
            else StackState.PRESENT
            for stack in deployed
        }

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
