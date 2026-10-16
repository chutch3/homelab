"""Reporting's one workflow: a trend, worked out once a day and kept."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from disktracker.catalog.schemas import DriveScope
from disktracker.reporting.repository import ReportingRepository
from disktracker.reporting.today import marks
from disktracker.reporting.trends import By, trends


class ReportingService:
    def __init__(self, repository: ReportingRepository, now: Callable[[], datetime]) -> None:
        self.repository, self.now = repository, now

    def trends(
        self, days: int, by: By | None, recent_days: int, scope: DriveScope
    ) -> dict[str, Any]:
        """The typical item price per terabyte on each day of a period, over the drives in scope
        and over each condition, capacity or store when asked. A trend of each scope is kept
        apart. A trend is kept once worked out, and
        worked out again, all of it, once anything it reads has changed: a price recorded (for
        any day, since prices can be entered backdated), changed or removed, an offer checked,
        moved or removed, a drive corrected, or a new day."""
        now = self.now()
        found = self.repository.kept_trend(days, by, recent_days, scope.key())
        kept = found.trend
        if (
            kept
            and kept["stamp"] == found.stamp
            and kept["revision"] == found.revision
            and kept["as_of"].astimezone(UTC).date() == now.astimezone(UTC).date()
        ):
            return cast(dict[str, Any], kept["body"])
        # The prices are read with the stamp and revision they are at, so the trend is kept
        # under exactly what it was worked out from; and worked out as of after they were read.
        changes = self.repository.price_changes(scope)
        now = self.now()
        body = trends(changes.offers, now, days, recent_days, by)
        self.repository.keep_trend(
            days, by, recent_days, scope.key(), body, now, changes.stamp, changes.revision
        )
        return body

    def prices_today(self, recent_days: int, scope: DriveScope) -> list[dict[str, Any]]:
        """What each drive in scope costs today in each condition it is in stock in, by the
        terabyte, cheapest first."""
        return marks(self.repository.latest_offers(scope), self.now(), recent_days)
