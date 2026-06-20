from __future__ import annotations

from datetime import datetime, timedelta

from warden.models import Anchor, QueueItem

# Statuses that legitimately make no download progress — never no-progress-removed.
_EXCLUDED = {"paused", "importing", "importPending", "completed"}


class ProgressTracker:
    """Pure cross-tick no-progress detector. An item is stale when it fails to download
    `min_progress_bytes` within `window_hours` (effective rate floor = bytes/window).
    Carries an anchor `(size_left, at)` per downloadId that advances on meaningful progress."""

    def __init__(self, *, window_hours: float, min_progress_bytes: int, enabled: bool = True) -> None:
        self._window = timedelta(hours=window_hours)
        self._min = min_progress_bytes
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
            elif anchor.size_left - it.size_left >= self._min:
                nxt[it.download_id] = Anchor(it.size_left, now)          # meaningful progress -> reset clock
            else:
                nxt[it.download_id] = anchor                            # hold the anchor
                if now - anchor.at >= self._window:
                    stale.append(it)                                    # no progress for too long
        return stale, nxt
