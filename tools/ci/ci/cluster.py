"""What the Swarm cluster currently holds, so a plan can say what will change.

Two list commands answer it: `docker stack ls` names what exists, `docker
service ls` gives each service its `running/desired` column. Every read asks
Docker for JSON, so nothing here parses formatted text. Nothing here writes —
a plan that mutated the thing it is describing would be a lie.

Converged means desired replicas *and* no update in flight; the reasoning for
both halves is in docs/architecture/overview.md, "What converged means".
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from ci.ports import CommandRunner

JSON_LINES = "{{json .}}"
STACK_LS = ["docker", "stack", "ls", "--format", JSON_LINES]
SERVICE_LS = ["docker", "service", "ls", "--format", JSON_LINES]
# `service ls` cannot report UpdateStatus, so every service is inspected at once.
# The template builds the object rather than `{{json .}}`, which would return the
# entire spec of every service — ~900KB on this cluster — to read one field.
UPDATE_FORMAT = (
    '{"Name":{{json .Spec.Name}},'
    '"Update":{{if .UpdateStatus}}{{json .UpdateStatus.State}}{{else}}"none"{{end}}}'
)
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


@dataclass(frozen=True)
class Service:
    """One service as the cluster reports it, and what that means for a deploy."""

    name: str
    # None when the replicas column could not be read: not zero, not equal —
    # simply unknown, which no rule may treat as evidence of anything.
    running: int | None
    desired: int | None
    update: str = "none"

    @classmethod
    def from_listing(cls, listed: dict[str, str], updates: dict[str, str]) -> "Service":
        """One `docker service ls` object. Docker's key names stop here.

        A service missing from `updates` was deleted between the two reads, which
        is indistinguishable from one that has never updated — neither is in flight.
        """
        name = listed["Name"]
        return cls.from_row(name, listed["Replicas"], updates.get(name, "none"))

    @classmethod
    def from_row(cls, name: str, replicas: str, update: str = "none") -> "Service":
        """A `service ls` row. An unreadable replicas column counts as no evidence."""
        if match := REPLICAS.match(replicas):
            return cls(name, int(match.group(1)), int(match.group(2)), update)
        return cls(name, running=None, desired=None, update=update)

    @property
    def at_desired_replicas(self) -> bool:
        return self.running is not None and self.running == self.desired

    @property
    def settled(self) -> bool:
        """No update still in flight, so the running tasks are the current ones."""
        return self.update not in UNSETTLED

    @property
    def converged(self) -> bool:
        return self.at_desired_replicas and self.settled


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
        deployed = [stack["Name"] for stack in self._objects(STACK_LS)]
        owned: dict[str, list[Service]] = defaultdict(list)
        for service in self._services():
            if owner := _owner(service.name, deployed):
                owned[owner].append(service)
        return {
            stack: StackState.CONVERGED
            if owned[stack] and all(service.converged for service in owned[stack])
            else StackState.PRESENT
            for stack in deployed
        }

    def _services(self) -> list[Service]:
        """Every service the cluster holds, with the facts both rules need."""
        listed = self._objects(SERVICE_LS)
        updates = self._update_states([service["Name"] for service in listed])
        return [Service.from_listing(service, updates) for service in listed]

    def _update_states(self, names: list[str]) -> dict[str, str]:
        """Service name -> update state. `inspect` with no arguments is an error."""
        if not names:
            return {}
        return {u["Name"]: u["Update"] for u in self._objects(SERVICE_INSPECT + names)}

    def _objects(self, argv: list[str]) -> list[dict[str, str]]:
        """One JSON object per line, which is what every read here asks Docker for."""
        outcome = self._commands.run(argv, capture=True)
        if not outcome.ok:
            raise ClusterUnreachable(f"{' '.join(argv[:3])} failed: {outcome.stderr.strip()}")
        try:
            return [json.loads(line) for line in outcome.stdout.splitlines() if line.strip()]
        except json.JSONDecodeError as exc:
            raise ClusterUnreachable(f"{' '.join(argv[:3])} returned unreadable JSON: {exc}")


def _owner(service: str, stacks: list[str]) -> str | None:
    """The stack a service belongs to: the longest name it is prefixed with.

    Stack names contain underscores (`actual_server`), so the prefix is only
    unambiguous against the set the cluster actually reports.
    """
    candidates = [s for s in stacks if service.startswith(f"{s}_")]
    return max(candidates, key=len) if candidates else None
