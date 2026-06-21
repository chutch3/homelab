from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from collections.abc import Sequence

from warden.models import QueueItem
from warden.services.stale import StaleDetector, StaleVerdict


@dataclass(frozen=True)
class RemoveAction:
    queue_id: int
    remote_id: int
    reason: str
    age_hours: float


@dataclass(frozen=True)
class SweepDecision:
    to_remove: tuple[RemoveAction, ...]
    skipped: bool
    queue_size: int
    stalled_count: int
    all_queued_remote_ids: frozenset[int]


class QueueSweeper:
    """Pure policy: detector + mass-unhealthy guard + per-tick cap + exclusion set."""

    def __init__(self, detector: StaleDetector, *, enabled: bool, max_removals_per_tick: int,
                 mass_fraction: float, min_queue_for_guard: int) -> None:
        self._detector = detector
        self._enabled = enabled
        self._max = max_removals_per_tick
        self._mass_fraction = mass_fraction
        self._min_queue = min_queue_for_guard

    def plan(self, queue: list[QueueItem], now: datetime,
             extra: Sequence[StaleVerdict] = ()) -> SweepDecision:
        verdicts = list(self._detector.detect(queue, now))
        seen = {v.item.id for v in verdicts}
        for v in extra:                          # e.g. no-progress verdicts, deduped by queue id
            if v.item.id not in seen:
                verdicts.append(v)
                seen.add(v.item.id)
        stalled = len(verdicts)
        total = len(queue)
        # Guard ONLY on the true outage signal: when the client is unreachable, *arr flips its
        # whole share to downloadClientUnavailable at once. Genuinely-stuck downloads (stalled /
        # no-progress, client up) are safe to remove+blocklist at any scale, so they don't bail.
        unavailable = sum(1 for q in queue if q.status == "downloadClientUnavailable")
        all_ids = frozenset(q.remote_id for q in queue)

        if total >= self._min_queue and unavailable / total > self._mass_fraction:
            return SweepDecision((), True, total, stalled, all_ids)
        if not self._enabled:
            return SweepDecision((), False, total, stalled, all_ids)

        actions = tuple(
            RemoveAction(queue_id=v.item.id, remote_id=v.item.remote_id, reason=v.reason,
                         age_hours=(now - v.item.added).total_seconds() / 3600.0)
            for v in verdicts[: self._max]
        )
        return SweepDecision(actions, False, total, stalled, all_ids)
