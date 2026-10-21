"""The catalog reads not yet given to their owners (Amendment B in the refactor plan): the drives to
manage, a drive and its offers, offers, prices, the Review queue and the condition rules. Every
read is one snapshot, so the queries it takes describe one moment; filtering, ordering and paging
are done by the database. Offers are read through catalog.offer_repository."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from disktracker.catalog.models import (
    ConditionRule,
    Drive,
    MpnAlias,
    Offer,
    Price,
    ReviewItem,
)
from disktracker.catalog.offer_repository import OfferRepository, holding
from disktracker.catalog.views import drive_view, price_view, review_item_view
from disktracker.database import SessionFactory


class CatalogQueries:
    def __init__(self, snapshot_factory: SessionFactory, offers: OfferRepository) -> None:
        self.snapshot_factory, self.offers = snapshot_factory, offers

    # Offers and their prices.

    def offer_summaries(
        self, store: str | None = None, drive_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        """Every offer, of one store or one drive when asked, with its latest price, by title."""
        chosen = select(Offer).order_by(Offer.title, Offer.id)
        if store is not None:
            chosen = chosen.where(Offer.store == store)
        if drive_id is not None:
            chosen = chosen.where(Offer.drive_id == drive_id)
        with self.snapshot_factory() as session:
            return self.offers.summaries(session, chosen)

    def offer(self, offer_id: UUID) -> dict[str, Any]:
        with self.snapshot_factory() as session:
            return self.offers.with_history(session, offer_id)

    def prices(
        self,
        drive_id: UUID | None,
        offer_id: UUID | None,
        since: datetime | None,
        until: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """The prices of a drive's offers, or of one offer, in effect at any time from since to
        until: those recorded in it, and the one each offer had as it opened. Oldest first, limit
        of them from offset, and how many there are in all."""
        offers = select(Offer.id).where(
            Offer.drive_id == drive_id if drive_id is not None else Offer.id == offer_id
        )
        wanted = [Price.offer_id.in_(offers)]
        if until is not None:
            wanted.append(Price.observed_at <= until)
        if since is not None:
            wanted.append((Price.observed_at >= since) | Price.id.in_(holding(offers, since)))
        with self.snapshot_factory() as session:
            total = session.scalar(select(func.count()).select_from(Price).where(*wanted)) or 0
            found = session.execute(
                select(Price, Drive.capacity_gb)
                .join(Offer, Offer.id == Price.offer_id)
                .join(Drive, Drive.id == Offer.drive_id)
                .where(*wanted)
                .order_by(Price.observed_at, Price.entered_at, Price.id)
                .limit(limit)
                .offset(offset)
            ).tuples()
            items = [
                {**price_view(price, capacity), "offer_id": str(price.offer_id)}
                for price, capacity in found
            ]
            return items, total

    def drive_capacity(self, mpn: str) -> int | None:
        """The capacity of the drive an MPN (or an alias of it) names; None for an unknown one."""
        with self.snapshot_factory() as session:
            capacity: int | None = session.scalar(
                select(Drive.capacity_gb).where(Drive.mpn == canonical_mpn(session, mpn))
            )
            return capacity

    # The Review queue, and the condition rules.

    def review_items(
        self, store: str | None, reason: str | None, limit: int | None, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        """The offers waiting for review, newest first: those seen at this store and waiting for
        this reason when given, limit of them from offset; and how many there are in all,
        whatever the limit, counted in the same snapshot."""
        wanted = [
            column == value
            for column, value in ((ReviewItem.store, store), (ReviewItem.reason, reason))
            if value is not None
        ]
        with self.snapshot_factory() as session:
            total = session.scalar(select(func.count()).select_from(ReviewItem).where(*wanted))
            items = list(
                session.scalars(
                    select(ReviewItem)
                    .where(*wanted)
                    .order_by(ReviewItem.last_seen_at.desc(), ReviewItem.id)
                    .limit(limit)
                    .offset(offset)
                )
            )
            drives = _drives_named(session, {item.mpn for item in items if item.mpn})
            return [
                review_item_view(item, drives.get(item.mpn or "")) for item in items
            ], total or 0

    def condition_rules(self) -> list[dict[str, Any]]:
        with self.snapshot_factory() as session:
            rules = session.scalars(select(ConditionRule).order_by(ConditionRule.position))
            return [{"pattern": rule.pattern, "condition": rule.condition} for rule in rules]


# Reading on a session already open.


def _drives_named(session: Session, mpns: set[str]) -> dict[str, dict[str, Any]]:
    """The drive each of these MPNs names, by its own MPN or as an alias of it."""
    by_alias = dict(
        session.execute(select(MpnAlias.alias, MpnAlias.drive_id).where(MpnAlias.alias.in_(mpns)))
        .tuples()
        .all()
    )
    found = session.scalars(
        select(Drive).where(Drive.mpn.in_(mpns) | Drive.id.in_(by_alias.values()))
    ).all()
    views = {drive.id: drive_view(drive, aliases_of(session, drive.id)) for drive in found}
    named = {drive.mpn: views[drive.id] for drive in found}
    return named | {alias: views[drive_id] for alias, drive_id in by_alias.items()}


def canonical_mpn(session: Session, mpn: str) -> str:
    """The MPN a drive is recorded under, for this MPN or an alias of it."""
    canonical = session.scalar(
        select(Drive.mpn).join(MpnAlias, MpnAlias.drive_id == Drive.id).where(MpnAlias.alias == mpn)
    )
    return canonical or mpn


def aliases_of(session: Session, drive_id: UUID) -> list[str]:
    return list(
        session.scalars(
            select(MpnAlias.alias).where(MpnAlias.drive_id == drive_id).order_by(MpnAlias.alias)
        )
    )
