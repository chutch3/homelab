"""What time it is, for whatever depends on it; tests stop it."""

from datetime import UTC, datetime


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)
