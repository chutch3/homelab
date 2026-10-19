"""What reporting reads and keeps: every change of every price, to work trends out from, and
each trend once worked out. Every operation opens its own session; the reads run in a snapshot,
so what a trend is worked out from and the revision it is kept under describe one moment."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import extract, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from disktracker.catalog.models import Drive, Offer, Price
from disktracker.catalog.queries import COUNTED, every_offer_facts, offer_facts, scope_filters
from disktracker.catalog.schemas import DriveScope
from disktracker.database import SessionFactory
from disktracker.reporting.models import Trend, TrendRevision
from disktracker.reporting.trends import Change
from disktracker.reporting.trends import Offer as Sold


class Kept:
    """A trend as kept, with the revision what trends read is at now."""

    def __init__(self, trend: dict[str, Any] | None, revision: int) -> None:
        self.trend, self.revision = trend, revision


class Changes:
    """Every offer with every change of its price, with the revision they are at."""

    def __init__(self, offers: list[Sold], revision: int) -> None:
        self.offers, self.revision = offers, revision


class ReportingRepository:
    def __init__(self, session_factory: SessionFactory, snapshot_factory: SessionFactory) -> None:
        self.session_factory, self.snapshot_factory = session_factory, snapshot_factory

    def kept_trend(self, days: int, by: str | None, recent_days: int, scope: str) -> Kept:
        """The trend kept for a period, split, allowance and scope (None when none has been), and
        where the prices stand now."""
        with self.snapshot_factory() as session:
            trend = session.get(Trend, (days, by or "", recent_days, scope))
            kept = None if trend is None else {
                "as_of": trend.as_of, "revision": trend.revision, "body": trend.body,
            }  # fmt: skip
            return Kept(kept, _revision(session))

    def price_changes(self, scope: DriveScope) -> Changes:
        """Every offer of the drives in scope with every change of its price, oldest first: what
        trends are read from; with the revision of that very moment."""
        with self.snapshot_factory() as session:
            return Changes(_price_changes(session, scope), _revision(session))

    def latest_offers(self, scope: DriveScope) -> list[dict[str, Any]]:
        """Every offer that counts (catalog.queries.COUNTED) of the drives in scope with its latest
        price and its drive's capacity: what today's prices are read from. An offer is checked whenever a price is recorded for
        it."""
        latest = (
            select(Price)
            .distinct(Price.offer_id)
            .order_by(
                Price.offer_id, Price.observed_at.desc(), Price.entered_at.desc(), Price.id.desc()
            )
            .subquery()
        )
        with self.snapshot_factory() as session:
            rows = session.execute(
                select(
                    Offer,
                    Drive.capacity_gb,
                    latest.c.item_price_cents,
                    latest.c.in_stock,
                    latest.c.observed_at,
                )
                .join(Drive, Drive.id == Offer.drive_id)
                .join(latest, latest.c.listing_id == Offer.id)
                .where(COUNTED, *_in_scope(scope))
            ).tuples()
            return [
                {
                    "id": offer.id,
                    "drive_id": offer.drive_id,
                    "condition": offer.condition,
                    "title": offer.title,
                    "capacity_gb": capacity_gb,
                    "item_price_cents": item_price_cents,
                    "in_stock": in_stock,
                    "last_checked_at": max(observed_at, offer.last_checked_at or observed_at),
                }
                for offer, capacity_gb, item_price_cents, in_stock, observed_at in rows
            ]

    def store_freshness(self) -> list[dict[str, Any]]:
        """Each store with offers, by key: how many it has, held ones and all, and when the
        latest and the middle of them were checked."""
        facts = every_offer_facts().subquery()
        middle = func.percentile_cont(0.5).within_group(extract("epoch", facts.c.checked))
        with self.snapshot_factory() as session:
            rows = session.execute(
                select(
                    facts.c.store,
                    func.count().label("offers"),
                    func.max(facts.c.checked).label("latest_checked_at"),
                    func.to_timestamp(middle).label("median_checked_at"),
                )
                .group_by(facts.c.store)
                .order_by(facts.c.store)
            ).mappings()
            return [dict(row) for row in rows]

    def keep_trend(
        self,
        days: int,
        by: str | None,
        recent_days: int,
        scope: str,
        body: dict[str, Any],
        as_of: datetime,
        revision: int,
    ) -> None:
        """Keep a trend in place of the one kept before for the same period, split, allowance and
        scope.
        as_of: when all of it was last worked out. revision: that of what it was worked out
        from."""
        kept = {"as_of": as_of, "revision": revision, "body": body}
        with self.session_factory() as session:
            session.execute(
                pg_insert(Trend)
                .values(days=days, by=by or "", recent_days=recent_days, scope=scope, **kept)
                .on_conflict_do_update(
                    index_elements=[Trend.days, Trend.by, Trend.recent_days, Trend.scope],
                    set_=kept,
                )
            )
            session.commit()


def _in_scope(scope: DriveScope) -> list[Any]:
    """What an offer must be to be of the drives in scope: as the drives list narrows them."""
    if scope.scope() == DriveScope():
        return []
    facts = offer_facts().subquery()
    return [Offer.id.in_(select(facts.c.id).where(*scope_filters(facts, scope)))]


def _price_changes(session: Session, scope: DriveScope) -> list[Sold]:
    changes: dict[UUID, list[Change]] = {}
    chosen = select(Offer.id).where(COUNTED, *_in_scope(scope))
    for offer_id, observed_at, item_price_cents, in_stock in session.execute(
        select(Price.offer_id, Price.observed_at, Price.item_price_cents, Price.in_stock)
        .where(Price.offer_id.in_(chosen))
        .order_by(Price.offer_id, Price.observed_at, Price.entered_at, Price.id)
    ).tuples():
        changes.setdefault(offer_id, []).append(Change(observed_at, item_price_cents, in_stock))
    offers = session.execute(
        select(Offer, Drive.capacity_gb)
        .join(Drive, Drive.id == Offer.drive_id)
        .where(COUNTED, *_in_scope(scope))
    ).tuples()
    return [
        Sold(
            drive=str(offer.drive_id),
            condition=offer.condition,
            store=offer.store,
            capacity_gb=capacity_gb,
            # An offer is checked whenever a price is recorded for it.
            last_checked_at=max(
                changes[offer.id][-1].at,
                offer.last_checked_at or datetime.min.replace(tzinfo=UTC),
            ),
            changes=changes[offer.id],
        )
        for offer, capacity_gb in offers
    ]


def _revision(session: Session) -> int:
    """How many times what a trend reads has changed."""
    return session.scalars(select(TrendRevision.revision)).one()
