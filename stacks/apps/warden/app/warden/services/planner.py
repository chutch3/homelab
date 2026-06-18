from __future__ import annotations

from warden.models import InstanceWanted, WantedItem


class HuntPlanner:
    """Selects up to `allowance` items, missing before cutoff-unmet,
    round-robin across instances so no single library starves.

    Each instance queue is ordered missing-first then cutoff-unmet, and a
    single round-robin loop cycles through all instances one item at a time
    until the allowance is reached or all queues are empty."""

    def plan(self, allowance: int, wanted: dict[str, InstanceWanted]) -> list[WantedItem]:
        if allowance <= 0:
            return []
        names = list(wanted.keys())
        queues: list[list[WantedItem]] = []
        for name in names:
            iw = wanted[name]
            queues.append(list(iw.missing) + list(iw.cutoff_unmet))

        selected: list[WantedItem] = []
        idx = 0
        while len(selected) < allowance and any(queues):
            q = queues[idx % len(queues)]
            if q:
                selected.append(q.pop(0))
            idx += 1
        return selected[:allowance]
