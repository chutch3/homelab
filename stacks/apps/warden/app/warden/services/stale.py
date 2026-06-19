from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from warden.models import QueueItem

_ACTIONABLE = {"warning", "failed"}


@dataclass(frozen=True)
class StaleVerdict:
    item: QueueItem
    reason: str  # "stalled" | "error"


class StaleDetector:
    """Pure: which queue items are removable-stale (status-based + grace)."""

    def __init__(self, grace_hours: float) -> None:
        self._grace = timedelta(hours=grace_hours)

    def detect(self, queue: list[QueueItem], now: datetime) -> list[StaleVerdict]:
        out: list[StaleVerdict] = []
        for it in queue:
            if it.status in _ACTIONABLE and it.error_message and (now - it.added) >= self._grace:
                reason = "stalled" if "stall" in it.error_message.lower() else "error"
                out.append(StaleVerdict(item=it, reason=reason))
        return out
