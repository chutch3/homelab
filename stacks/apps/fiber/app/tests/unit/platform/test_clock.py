from __future__ import annotations

from datetime import timezone

from fiber.platform.clock import SystemClock


def test_system_clock_returns_utc() -> None:
    result = SystemClock().now()
    assert result.tzinfo is not None
    assert result.tzinfo == timezone.utc or result.utcoffset().total_seconds() == 0
