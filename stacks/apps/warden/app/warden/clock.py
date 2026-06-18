from __future__ import annotations

from datetime import datetime, timezone


class SystemClock:
    """Wall-clock source, injectable so tests can supply a fixed time."""

    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)
