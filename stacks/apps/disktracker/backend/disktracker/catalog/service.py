"""The catalog reads not yet given to their owners (Amendment B in the refactor plan): each moves to
the owner of the question it answers, and this goes with the last of them. Every change has its
own service (catalog.*_service)."""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from disktracker.catalog.queries import CatalogQueries
from disktracker.catalog.schemas import (
    OfferQuery,
    PriceQuery,
)


class CatalogService:
    def __init__(self, queries: CatalogQueries, now: Callable[[], datetime]) -> None:
        self.queries, self.now = queries, now

    # Reading drives, offers and prices.

    def list_offers(self, query: OfferQuery) -> list[dict[str, Any]]:
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
