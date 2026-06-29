from __future__ import annotations

from datetime import datetime, timedelta

from warden.models import Anchor, QueueItem

# Statuses with a flat sizeleft by design — never no-progress-removed. `queued` is
# the load-bearing one: a download waiting in a backlogged client hasn't started, so
# flagging it would blocklist a healthy download waiting its turn. (Pre-grab states
# like `delay` carry no downloadId and are skipped by the guard in evaluate().)
_EXCLUDED = {"paused", "importing", "importPending", "completed", "queued"}


class ProgressTracker:
    """Pure cross-tick no-progress detector. Flags an item only when its
    bytes-remaining stays frozen (drains by <= `jitter_tolerance_bytes`) for the
    whole `window_hours`; any real progress resets its per-downloadId anchor, so a
    slow-but-alive download is never flagged — only a genuinely stuck one."""

    def __init__(self, *, window_hours: float, jitter_tolerance_bytes: int = 0, enabled: bool = True) -> None:
        self._window = timedelta(hours=window_hours)
        self._tolerance = jitter_tolerance_bytes
        self._enabled = enabled

    def evaluate(self, queue: list[QueueItem], prior: dict[str, Anchor], now: datetime
                 ) -> tuple[list[QueueItem], dict[str, Anchor]]:
        if not self._enabled:
            return [], {}
        stale: list[QueueItem] = []
        nxt: dict[str, Anchor] = {}
        for it in queue:
            if not it.download_id or it.status in _EXCLUDED:
                continue
            anchor = prior.get(it.download_id)
            if anchor is None:
                nxt[it.download_id] = Anchor(it.size_left, now)          # first sighting
            elif anchor.size_left - it.size_left > self._tolerance:
                nxt[it.download_id] = Anchor(it.size_left, now)          # progress -> reset clock
            else:
                nxt[it.download_id] = anchor                            # frozen -> hold the anchor
                if now - anchor.at >= self._window:
                    stale.append(it)                                    # no progress for too long
        return stale, nxt
