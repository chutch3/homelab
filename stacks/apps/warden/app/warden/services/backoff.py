from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class BackoffOutcome:
    clear: frozenset[int]                    # remote_ids to drop (a grab reset their streak)
    upsert: dict[int, tuple[int, float]]     # remote_id -> (miss_streak, until_epoch; 0.0 = inactive)
    entered: int                             # items that (re)entered cooldown this round


class BackoffTracker:
    """Pure policy: after `threshold` consecutive misses an item earns a `cooldown` during
    which it is excluded from hunting; a grab clears its streak. Persistence lives in the repo.

    Like EfficacyTracker, the `enabled` flag is gated by the orchestrator, not checked here."""

    def __init__(self, *, enabled: bool, threshold: int, cooldown: timedelta) -> None:
        self.enabled = enabled
        self._threshold = threshold
        self._cooldown = cooldown

    def decide(self, streaks: Mapping[int, int], hit_ids: Sequence[int],
               miss_ids: Sequence[int], now: datetime) -> BackoffOutcome:
        until = (now + self._cooldown).timestamp()
        upsert: dict[int, tuple[int, float]] = {}
        entered = 0
        for rid in miss_ids:
            streak = streaks.get(rid, 0) + 1
            if streak >= self._threshold:
                upsert[rid] = (streak, until)
                entered += 1
            else:
                upsert[rid] = (streak, 0.0)
        return BackoffOutcome(frozenset(hit_ids), upsert, entered)
