"""What the cluster's facts mean for a deploy.

A stack is not a Swarm object — it is a label. `docker stack deploy` stamps
every service it creates with `com.docker.stack.namespace`, and `docker stack
ls` is that grouping, nothing more. So a stack has no state of its own: whether
it is CONVERGED is decided entirely by the services carrying its label.

Nothing here runs anything. Facts in (:mod:`ci.docker`), verdict out.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

# Swarm's replicas column: `1/1`, or `1/1 (max 1 per node)` under a placement limit.
REPLICAS = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")

# An update still moving, or stopped needing a human. Anything else is settled.
UNSETTLED = frozenset({"updating", "paused", "rollback_started"})


class StackState(Enum):
    ABSENT = "absent"
    PRESENT = "present"
    CONVERGED = "converged"


@dataclass(frozen=True)
class Service:
    """One service as the cluster reports it, and what that means for a deploy."""

    name: str
    stack: str
    # None when the replicas column could not be read: not zero, not equal —
    # simply unknown, which no rule may treat as evidence of anything.
    running: int | None
    desired: int | None
    update: str = "none"

    @classmethod
    def from_row(cls, name: str, stack: str, replicas: str, update: str = "none") -> "Service":
        """An unreadable replicas column counts as no evidence, not as zero."""
        if match := REPLICAS.match(replicas):
            return cls(name, stack, int(match.group(1)), int(match.group(2)), update)
        return cls(name, stack, running=None, desired=None, update=update)

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


def stack_states(services: list[Service]) -> dict[str, StackState]:
    """Each deployed stack's state. A stack absent from the map was never deployed."""
    owned: dict[str, list[Service]] = defaultdict(list)
    for service in services:
        if service.stack:
            owned[service.stack].append(service)
    return {
        stack: StackState.CONVERGED
        if all(service.converged for service in owned[stack])
        else StackState.PRESENT
        for stack in owned
    }
