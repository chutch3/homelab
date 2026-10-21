"""The catalog reads not yet given to their owners (Amendment B in the refactor plan): the drives to
manage, a drive and its offers, offers, prices, the Review queue and the condition rules. Every
read is one snapshot, so the queries it takes describe one moment; filtering, ordering and paging
are done by the database. Offers are read through catalog.offer_repository."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, true
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
from disktracker.catalog.schemas import CatalogDriveQuery
from disktracker.catalog.views import drive_view, price_view, review_item_view
from disktracker.database import SessionFactory
from disktracker.errors import DriveNotFound
from disktracker.facts import (
    COUNTED,
    SCALAR_SPECIFICATIONS,
    UNKNOWN,
    escaped,
    every_offer_facts,
    named_by,
    offer_facts,
)


class CatalogQueries:
    def __init__(self, snapshot_factory: SessionFactory, offers: OfferRepository) -> None:
        self.snapshot_factory, self.offers = snapshot_factory, offers

    def catalog_drives(self, query: CatalogDriveQuery, now: datetime) -> dict[str, Any]:
        """Every drive, those with no offer and those with held offers too, that the words match
        by its MPN, another of its MPNs, or any name an offer of it goes by: a page of them, one
        named by the words first, then in stock first and cheapest terabyte first, as each is
        shown by its cheapest offer in stock (else its cheapest), and a drive with no offer after
        those with one, by MPN. Each comes with how many offers it has and what it needs, and how
        many of every drive need each thing."""
        facts = every_offer_facts().subquery()
        by_drive = {"partition_by": facts.c.drive_id}
        named = named_by(facts, query.q) if query.q else true()
        stale = and_(facts.c.in_stock, facts.c.checked < now - timedelta(days=query.recent_days))
        ranked = (
            select(
                facts,
                func.row_number()
                .over(**by_drive, order_by=(facts.c.in_stock.desc(), facts.c.per_tb, facts.c.id))
                .label("rank"),
                func.count().over(**by_drive).label("offers"),
                func.bool_or(stale).over(**by_drive).label("stale"),
                func.bool_or(named).over(**by_drive).label("named"),
            )
        ).subquery()
        offered = select(ranked).where(ranked.c.rank == 1).subquery()
        aliases = (
            select(MpnAlias.drive_id, func.string_agg(MpnAlias.alias, " ").label("names"))
            .group_by(MpnAlias.drive_id)
            .subquery()
        )
        own_names = func.concat_ws(" ", Drive.mpn, aliases.c.names)
        own = own_names.ilike(f"%{escaped(query.q)}%", escape="\\") if query.q else true()
        shown = (
            select(
                Drive.id.label("drive_id"),
                Drive.mpn,
                Drive.specifications,
                func.coalesce(offered.c.title, Drive.mpn).label("title"),
                func.coalesce(offered.c.offers, 0).label("offers"),
                func.coalesce(offered.c.stale, False).label("stale"),
                func.coalesce(offered.c.in_stock, False).label("in_stock"),
                offered.c.per_tb,
                (func.coalesce(offered.c.named, False) | own).label("named"),
            )
            .outerjoin(offered, offered.c.drive_id == Drive.id)
            .outerjoin(aliases, aliases.c.drive_id == Drive.id)
        ).subquery()
        specs = shown.c.specifications
        unknown = and_(
            *(
                func.coalesce(specs[key].astext, UNKNOWN) == UNKNOWN
                for key in SCALAR_SPECIFICATIONS
            ),
            func.coalesce(func.jsonb_array_length(specs["intended_use"]), 0) == 0,
        )
        need = {"unknown_specifications": unknown, "stale": shown.c.stale}
        # Those the words are the MPN, or another MPN, of come first.
        first = (
            [
                shown.c.drive_id.in_(
                    select(Drive.id)
                    .where(func.upper(Drive.mpn) == query.q.upper())
                    .union(
                        select(MpnAlias.drive_id).where(
                            func.upper(MpnAlias.alias) == query.q.upper()
                        )
                    )
                ).desc()
            ]
            if query.q
            else []
        )
        wanted = [shown.c.named, need[query.issue] if query.issue else true()]
        with self.snapshot_factory() as session:
            rows = session.execute(
                select(shown, unknown.label("unknown"))
                .where(*wanted)
                .order_by(
                    *first,
                    shown.c.in_stock.desc(),
                    shown.c.per_tb.asc().nulls_last(),
                    shown.c.mpn,
                    shown.c.drive_id,
                )
                .limit(query.limit)
                .offset(query.offset)
            ).all()
            counted = session.execute(
                select(
                    func.count().filter(and_(*wanted)),
                    func.count(),
                    *(func.count().filter(value) for value in need.values()),
                ).select_from(shown)
            ).one()
            found = {
                drive.id: drive
                for drive in session.scalars(
                    select(Drive).where(Drive.id.in_([row.drive_id for row in rows]))
                )
            }
            return {
                "items": [
                    {
                        "drive": drive_view(found[row.drive_id], aliases_of(session, row.drive_id)),
                        "title": row.title,
                        "offers": row.offers,
                        "issues": [
                            name
                            for name, needed in (
                                ("unknown_specifications", row.unknown),
                                ("stale", row.stale),
                            )
                            if needed
                        ],
                    }
                    for row in rows
                ],
                "total": counted[0],
                "all": counted[1],
                "issues": dict(zip(need, counted[2:], strict=True)),
                "limit": query.limit,
                "offset": query.offset,
            }

    def drive_detail(self, drive_id: UUID, since: datetime) -> dict[str, Any]:
        """A drive with every offer of it, held ones too, and of those that count (COUNTED) each
        one's prices in effect from a moment on and when it was last checked: what the range of
        each condition is drawn from."""
        with self.snapshot_factory() as session:
            drive = session.get(Drive, drive_id)
            if drive is None:
                raise DriveNotFound()
            chosen = select(Offer).where(Offer.drive_id == drive_id).order_by(Offer.title, Offer.id)
            offers = self.offers.summaries(session, chosen)
            counted = {
                str(offer_id)
                for offer_id in session.scalars(
                    select(Offer.id).where(Offer.drive_id == drive_id, COUNTED)
                )
            }
            windows = self.offers.prices_since(
                session, [UUID(offer_id) for offer_id in counted], since
            )
            return {
                "drive": drive_view(drive, aliases_of(session, drive_id)),
                "offers": offers,
                "kin": [
                    (offer["condition"], windows[offer["id"]],
                     datetime.fromisoformat(offer["last_checked_at"]))
                    for offer in offers
                    if offer["id"] in counted
                ],
            }  # fmt: skip

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

    def offers_to_recheck(self, now: datetime, recent_days: int) -> list[dict[str, Any]]:
        """Offers entered by hand and not checked within recent_days, longest unchecked first:
        a collected offer is the collector's to check."""
        facts = offer_facts().subquery()
        overdue = (
            select(facts.c.id)
            .where(
                facts.c.provenance == "manual",
                (facts.c.checked < now - timedelta(days=recent_days)) | (facts.c.checked > now),
            )
            .order_by(facts.c.checked, facts.c.id)
        )
        with self.snapshot_factory() as session:
            ids = list(session.scalars(overdue))
            found = {
                offer["id"]: offer
                for offer in self.offers.summaries(session, select(Offer).where(Offer.id.in_(ids)))
            }
            return [found[str(offer_id)] for offer_id in ids]

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
