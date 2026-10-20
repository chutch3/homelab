"""The catalog's application behavior: recording prices, deciding what queued offers are,
correcting drives and offers, and the condition rules. It applies what a request means and asks
the repository for whole operations. An operation over several repositories opens one session,
hands it to each, and commits once (the shared-session convention); the repositories never
commit."""

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.queries import CatalogQueries
from disktracker.catalog.repository import CatalogRepository
from disktracker.catalog.schemas import (
    CatalogDriveQuery,
    ConditionRule,
    DriveEdit,
    DriveInput,
    DriveQuery,
    OfferEdit,
    OfferQuery,
    PriceQuery,
    RangeQuery,
)
from disktracker.catalog.views import drive_view
from disktracker.database import SessionFactory
from disktracker.reporting.ranges import price_range


class CatalogService:
    def __init__(
        self,
        repository: CatalogRepository,
        queries: CatalogQueries,
        now: Callable[[], datetime],
        session_factory: SessionFactory,
        drives: DriveRepository,
    ) -> None:
        self.repository, self.queries, self.now = repository, queries, now
        self.session_factory, self.drive_repository = session_factory, drives

    # Making drives.

    def create_drive(self, entry: DriveInput) -> dict[str, Any]:
        """A drive made on its own, before any price of it."""
        with self.session_factory() as session:
            drive = self.drive_repository.create(
                session,
                mpn=entry.mpn,
                capacity_gb=entry.capacity_gb,
                brand=entry.brand,
                specifications=entry.specifications.model_dump(mode="json"),
            )
            session.commit()
            return drive_view(drive, [])

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

    # Recording a price.

    # The review queue.

    def review_items(
        self,
        store: str | None = None,
        reason: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        return self.queries.review_items(store, reason, limit, offset)

    # Drives and the MPNs they go by.

    def add_alias(self, drive_id: UUID, alias: str) -> dict[str, Any]:
        return self.repository.add_alias(drive_id, alias)

    def edit_drive(self, drive_id: UUID, entry: DriveEdit) -> dict[str, Any]:
        """Correct what is given of a drive, and leave the rest as it is."""
        given = entry.model_dump(mode="json", exclude_unset=True)
        values = {key: given[key] for key in ("capacity_gb", "brand") if key in given}
        return self.repository.edit_drive(drive_id, values, given.get("specifications"))

    # Offers and prices, corrected.

    def edit_offer(self, offer_id: UUID, entry: OfferEdit) -> dict[str, Any]:
        fields = entry.model_dump(exclude_unset=True)
        if "url" in fields:
            fields["url"] = str(fields["url"]) if fields["url"] else None
        return self.repository.edit_offer(offer_id, fields)

    def delete_offer(self, offer_id: UUID) -> None:
        self.repository.delete_offer(offer_id)

    def delete_price(self, price_id: UUID) -> None:
        self.repository.delete_price(price_id)

    # The rules that read a condition from listing text.

    def list_condition_rules(self) -> list[dict[str, Any]]:
        return self.queries.condition_rules()

    def replace_condition_rules(self, rules: Sequence[ConditionRule]) -> list[dict[str, Any]]:
        """The rules, in the order given, in place of the ones kept before."""
        kept = [rule.model_dump() for rule in rules]
        self.repository.replace_condition_rules(kept)
        return kept
