from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _zone(tz: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


class ResetSchedule:
    """The daily quota window, parsed once from a ``HH:MM`` reset time evaluated
    in the configured timezone (defaults to UTC). ``now`` may be in any tz; it is
    converted to the schedule's tz before computing the window."""

    def __init__(self, reset_at_local: str, tz: str = "UTC") -> None:
        hour, minute = (int(p) for p in reset_at_local.split(":"))
        self._hour = hour
        self._minute = minute
        self._tz = _zone(tz)

    def _reset_today(self, now: datetime) -> datetime:
        local = now.astimezone(self._tz)
        return local.replace(hour=self._hour, minute=self._minute, second=0, microsecond=0)

    def window_key(self, now: datetime) -> str:
        """YYYY-MM-DD key (in the schedule's tz) of the window containing ``now``."""
        reset_today = self._reset_today(now)
        local = now.astimezone(self._tz)
        start = reset_today if local >= reset_today else reset_today - timedelta(days=1)
        return start.date().isoformat()

    def next_reset(self, now: datetime) -> datetime:
        """The next reset boundary at/after ``now`` (tz-aware, in the schedule's tz)."""
        reset_today = self._reset_today(now)
        local = now.astimezone(self._tz)
        return reset_today if local < reset_today else reset_today + timedelta(days=1)
