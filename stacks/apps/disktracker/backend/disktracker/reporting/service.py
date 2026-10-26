"""Reporting: the market as the Prices page reads it, trends (worked out once a day and kept),
today's prices and how fresh each store's prices are."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from disktracker.catalog.schemas import DriveScope
from disktracker.clock import Clock
from disktracker.database import Transactions
from disktracker.reporting.ranges import price_range
from disktracker.reporting.repository import ReportingRepository
from disktracker.reporting.schemas import InventoryQuery, MarketQuery, PriceRangeQuery
from disktracker.reporting.today import marks
from disktracker.reporting.trends import By, trends


def kept_as(scope: DriveScope) -> str:
    """What a trend of these drives is kept under: the same for the same drives asked for,
    however written. Choices within a filter are ORed, so their order and repeats narrow
    nothing; the words searched for are kept as typed. Empty for every drive."""
    given = scope.scope().model_dump(mode="json", exclude_defaults=True)
    chosen = {
        name: sorted(set(value)) if isinstance(value, list) else value
        for name, value in given.items()
    }
    return json.dumps(chosen, sort_keys=True) if chosen else ""


def still_stands(kept: dict[str, Any], revision: int, now: datetime) -> bool:
    """How long a kept trend lasts: until anything it reads changes (its revision), or the UTC
    day it was worked out on ends, since its days are counted back from today."""
    return (
        kept["revision"] == revision
        and kept["as_of"].astimezone(UTC).date() == now.astimezone(UTC).date()
    )


class ReportingService:
    def __init__(
        self, transactions: Transactions, repository: ReportingRepository, clock: Clock
    ) -> None:
        self.transactions, self.repository, self.clock = transactions, repository, clock

    def trends(
        self, days: int, by: By | None, recent_days: int, scope: DriveScope
    ) -> dict[str, Any]:
        """The typical item price per terabyte on each day of a period, over the drives in scope
        and over each condition, capacity or store when asked. A trend of each scope is kept
        apart, once worked out, while it still stands."""
        # The prices are read as of the same moment as the revision they are at, so the trend is
        # kept under exactly what it was worked out from; and worked out as of after they were
        # read, and kept apart from the read.
        with self.transactions.begin(reads=True):
            found = self.repository.kept_trend(days, by, recent_days, kept_as(scope))
            if found.trend and still_stands(found.trend, found.revision, self.clock.now()):
                return cast(dict[str, Any], found.trend["body"])
            changes = self.repository.price_changes(scope)
        now = self.clock.now()
        body = trends(changes.offers, now, days, recent_days, by)
        with self.transactions.begin():
            self.repository.keep_trend(
                days, by, recent_days, kept_as(scope), body, now, changes.revision
            )
        return body

    def market(self, query: MarketQuery) -> dict[str, Any]:
        """A part of the market, each drive with the range of its price over the days asked for,
        in the condition it is shown in."""
        with self.transactions.begin(reads=True):
            now = self.clock.now()
            read = self.repository.market(query, now)
            items = [
                listed.row
                | {"range": price_range(listed.prices, now, query.range_days, query.recent_days)}
                for listed in read.listed
            ]
            return {"items": items, **read.page}

    def price_ranges(self, query: PriceRangeQuery) -> dict[str, Any]:
        """The range of a drive's lowest item price in each condition it is offered in over the
        days asked for: null in one no offer of it was in stock in."""
        with self.transactions.begin(reads=True):
            now = self.clock.now()
            since = now - timedelta(days=query.range_days)
            by_condition: dict[str, list[Any]] = {}
            for condition, prices, checked in self.repository.range_inputs(query.drive_id, since):
                by_condition.setdefault(condition, []).append((prices, checked))
            return {
                condition: price_range(offers, now, query.range_days, query.recent_days)
                for condition, offers in by_condition.items()
            }

    def drive_inventory(self, query: InventoryQuery) -> dict[str, Any]:
        """A part of every drive to manage, each with how many offers it has and what it needs."""
        with self.transactions.begin(reads=True):
            return self.repository.drive_inventory(query, self.clock.now())

    def rechecks(self, recent_days: int) -> list[dict[str, Any]]:
        """The offers entered by hand due a check, longest unchecked first."""
        with self.transactions.begin(reads=True):
            return self.repository.rechecks(self.clock.now(), recent_days)

    def prices_today(self, recent_days: int, scope: DriveScope) -> list[dict[str, Any]]:
        """What each drive in scope costs today in each condition it is in stock in, by the
        terabyte, cheapest first."""
        with self.transactions.begin(reads=True):
            return marks(self.repository.latest_offers(scope), self.clock.now(), recent_days)

    def store_freshness(self) -> list[dict[str, Any]]:
        """How fresh each store's prices are."""
        with self.transactions.begin(reads=True):
            return self.repository.store_freshness()
