from __future__ import annotations

from datetime import datetime, timezone

from warden.models import InstanceWanted, WantedItem

_NEVER = datetime(1, 1, 1, tzinfo=timezone.utc)  # sentinel: never-searched sorts first


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
            # least-recently-searched first (never-searched before oldest); stable among equal
            missing = sorted(iw.missing, key=lambda w: w.last_search_time or _NEVER)
            queues.append(missing + list(iw.cutoff_unmet))

        selected: list[WantedItem] = []
        idx = 0
        while len(selected) < allowance and any(queues):
            q = queues[idx % len(queues)]
            if q:
                selected.append(q.pop(0))
            idx += 1
        return selected[:allowance]
