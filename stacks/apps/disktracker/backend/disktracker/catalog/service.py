"""The catalog reads not yet given to their owners (Amendment B in the refactor plan): each moves to
the owner of the question it answers, and this goes with the last of them. Every change has its
own service (catalog.*_service)."""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from disktracker.catalog.queries import CatalogQueries
from disktracker.catalog.schemas import (
    CatalogDriveQuery,
    DriveQuery,
    OfferQuery,
    PriceQuery,
    RangeQuery,
)
from disktracker.reporting.ranges import price_range


class CatalogService:
    def __init__(self, queries: CatalogQueries, now: Callable[[], datetime]) -> None:
        self.queries, self.now = queries, now

    # Reading drives, offers and prices.

    def catalog_drives(self, query: CatalogDriveQuery) -> dict[str, Any]:
        """A page of every drive to manage, with what each needs."""
        return self.queries.catalog_drives(query, self.now())

    def drives(self, query: DriveQuery) -> dict[str, Any]:
        """A page of the drive list, each drive with the range of its price over the days asked
        for, in the condition it is shown in."""
        now = self.now()
        page = self.queries.drive_page(query, now)
        for row in page["items"]:
            row["range"] = price_range(row.pop("kin"), now, query.range_days, query.recent_days)
        return page

    def drive(self, drive_id: UUID, query: RangeQuery) -> dict[str, Any]:
        """A drive with its offers, and the range of its price in each condition it is offered
        in over the days asked for."""
        now = self.now()
        found = self.queries.drive_detail(drive_id, now - timedelta(days=query.range_days))
        by_condition: dict[str, list[Any]] = {}
        for condition, prices, checked in found.pop("kin"):
            by_condition.setdefault(condition, []).append((prices, checked))
        found["ranges"] = {
            condition: price_range(offers, now, query.range_days, query.recent_days)
            for condition, offers in by_condition.items()
        }
        return found

    def list_offers(self, query: OfferQuery) -> list[dict[str, Any]]:
        if query.needs_recheck:
            return self.queries.offers_to_recheck(self.now(), query.recent_days)
        return self.queries.offer_summaries(query.store, query.drive_id)

    def prices(self, query: PriceQuery) -> dict[str, Any]:
        items, total = self.queries.prices(
            query.drive_id, query.offer_id, query.since, query.until, query.limit, query.offset
        )
        return {"items": items, "total": total, "limit": query.limit, "offset": query.offset}

    def offer(self, offer_id: UUID) -> dict[str, Any]:
        return self.queries.offer(offer_id)

    # The review queue.

    def review_items(
        self,
        store: str | None = None,
        reason: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        return self.queries.review_items(store, reason, limit, offset)

    # The rules that read a condition from listing text.

    def list_condition_rules(self) -> list[dict[str, Any]]:
        return self.queries.condition_rules()
