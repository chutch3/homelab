"""What reporting reads and keeps: the market as the Prices page lists it, every change of every
price, to work trends out from, and each trend once worked out. Every operation opens its own
session; the reads run in a snapshot, so what a report is worked out from (and the revision a
trend is kept under) describe one moment. Offers are read through catalog.offer_repository."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, extract, func, select, true
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.models import Drive, MpnAlias, Offer, Price
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.rules import SCALAR_SPECIFICATIONS, UNKNOWN
from disktracker.catalog.schemas import DriveScope
from disktracker.database import SessionFactory
from disktracker.facts import (
    COUNTED,
    escaped,
    every_offer_facts,
    latest_prices,
    named_by,
    offer_facts,
    scope_filters,
)
from disktracker.reporting.models import Trend, TrendRevision
from disktracker.reporting.schemas import InventoryQuery, MarketQuery
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


CONDITIONS = ("new", "manufacturer_recertified", "refurbished", "used")


@dataclass(frozen=True)
class Listed:
    """A drive of the market as read: its row but for its range, and what its range is drawn
    from (the prices of every offer of it that counts in the shown offer's condition, each with
    when that offer was last checked)."""

    row: dict[str, Any]
    prices: list[tuple[list[dict[str, Any]], datetime]]


@dataclass(frozen=True)
class MarketRead:
    """A part of the market as read: its drives, and what is said of every match."""

    listed: list[Listed]
    page: dict[str, Any]


class ReportingRepository:
    def __init__(
        self,
        session_factory: SessionFactory,
        snapshot_factory: SessionFactory,
        offers: OfferRepository,
        drives: DriveRepository,
    ) -> None:
        self.session_factory, self.snapshot_factory = session_factory, snapshot_factory
        self.offers, self.drives = offers, drives

    def range_inputs(
        self, drive_id: UUID, since: datetime
    ) -> list[tuple[str, list[dict[str, Any]], datetime]]:
        """What a drive's range in each condition is drawn from: each offer of it that counts
        (offer_facts), by condition, with its prices in effect from a moment on and when it was
        last checked."""
        facts = offer_facts().subquery()
        with self.snapshot_factory() as session:
            offers = session.execute(
                select(facts.c.id, facts.c.condition, facts.c.checked)
                .where(facts.c.drive_id == drive_id)
                .order_by(facts.c.title, facts.c.id)
            ).all()
            windows = self.offers.prices_since(session, [offer.id for offer in offers], since)
            return [(offer.condition, windows[str(offer.id)], offer.checked) for offer in offers]

    def drive_inventory(self, query: InventoryQuery, now: datetime) -> dict[str, Any]:
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
            return {
                "items": [
                    {
                        "drive": self.drives.view(session, row.drive_id),
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

    def rechecks(self, now: datetime, recent_days: int) -> list[dict[str, Any]]:
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

    def market(self, query: MarketQuery, now: datetime) -> MarketRead:
        """The drives with an offer that matches, a page of them, each shown by its cheapest
        matching offer in stock (else its cheapest matching offer), drives in stock first, then
        in the order asked for; with how many stores and sellers offer each and what each
        condition costs among the matches, and what each one's range is drawn from: the prices of
        every offer of it in the condition it is shown in, in effect from range_days ago to now.
        With what is said of every match, the filter options of every drive, and how many drives
        there are to buy at all."""
        facts = offer_facts().subquery()
        matching = select(facts).where(*_filters(facts, query, now)).subquery()
        rank = func.row_number().over(
            partition_by=matching.c.drive_id,
            order_by=(matching.c.in_stock.desc(), matching.c.per_tb, matching.c.id),
        )
        ranked = select(matching, rank.label("rank")).subquery()
        shown = select(ranked).where(ranked.c.rank == 1).subquery()
        sort_by = {
            "unit": shown.c.per_tb,
            "total": shown.c.total,
            "capacity": shown.c.capacity_gb,
            "checked": shown.c.checked,
        }[query.sort.split("-")[0]]
        ordering = sort_by.desc() if query.sort.endswith("-desc") else sort_by.asc()
        with self.snapshot_factory() as session:
            page = session.execute(
                select(shown.c.drive_id, shown.c.id, shown.c.condition)
                .order_by(shown.c.in_stock.desc(), ordering, shown.c.id)
                .limit(query.limit)
                .offset(query.offset)
            ).all()
            total = session.scalar(select(func.count()).select_from(shown)) or 0
            offers = session.scalar(select(func.count()).select_from(matching)) or 0
            catalogued = session.scalar(select(func.count(func.distinct(facts.c.drive_id)))) or 0
            sold_out = 0
            if query.in_stock:
                any_stock = query.model_copy(update={"in_stock": False})
                everything = select(facts.c.drive_id).where(*_filters(facts, any_stock, now))
                drives = session.scalar(
                    select(func.count(func.distinct(everything.subquery().c.drive_id)))
                )
                sold_out = (drives or 0) - total
            on_page = [row.drive_id for row in page]
            shown_offers = {
                offer["id"]: offer
                for offer in self.offers.summaries(
                    session, select(Offer).where(Offer.id.in_([row.id for row in page]))
                )
            }
            stores = dict(
                session.execute(
                    select(matching.c.drive_id, func.count(func.distinct(matching.c.sold_by)))
                    .where(matching.c.drive_id.in_(on_page))
                    .group_by(matching.c.drive_id)
                )
                .tuples()
                .all()
            )
            in_stock = matching.c.in_stock.is_(True)
            conditions: dict[UUID, dict[str, dict[str, Any]]] = {}
            for drive_id, condition, count, stocked, lowest in session.execute(
                select(
                    matching.c.drive_id,
                    matching.c.condition,
                    func.count(),
                    func.count().filter(in_stock),
                    func.min(matching.c.total).filter(in_stock),
                )
                .where(matching.c.drive_id.in_(on_page))
                .group_by(matching.c.drive_id, matching.c.condition)
            ).tuples():
                conditions.setdefault(drive_id, {})[condition] = {
                    "condition": condition, "offers": count, "in_stock": stocked,
                    "lowest_total_cents": lowest,
                }  # fmt: skip
            # Every offer of each drive on the page in the condition it is shown in, of those that
            # count (offer_facts): a held offer's price is no price of its drive's.
            kin = (
                session.execute(
                    select(facts.c.id, facts.c.drive_id, facts.c.condition, facts.c.checked)
                    .where(
                        func.row(facts.c.drive_id, facts.c.condition).in_(
                            [func.row(row.drive_id, row.condition) for row in page]
                        )
                    )
                    .order_by(facts.c.title, facts.c.id)
                ).all()
                if page
                else []
            )
            windows = self.offers.prices_since(
                session, [offer.id for offer in kin], now - timedelta(days=query.range_days)
            )
            listed = []
            for row in page:
                offer = shown_offers[str(row.id)]
                drawn_from = [
                    (windows[str(kin_offer.id)], kin_offer.checked)
                    for kin_offer in kin
                    if (kin_offer.drive_id, kin_offer.condition) == (row.drive_id, row.condition)
                ]
                listed.append(
                    Listed(
                        {
                            "drive": offer["drive"],
                            "offer": offer,
                            "stores": stores[row.drive_id],
                            "conditions": [
                                conditions[row.drive_id][condition]
                                for condition in CONDITIONS
                                if condition in conditions[row.drive_id]
                            ],
                        },
                        drawn_from,
                    )
                )
            return MarketRead(
                listed,
                {
                    "total": total,
                    "offers": offers,
                    "sold_out": sold_out,
                    "catalogued": catalogued,
                    "limit": query.limit,
                    "offset": query.offset,
                    "as_of": now,
                    "lowest": _lowest(session, matching, now, query.recent_days),
                    "filter_options": _filter_options(session, facts, query, now),
                },
            )

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
        """Every offer that counts (disktracker.facts.COUNTED) of the drives in scope with its latest
        price and its drive's capacity: what today's prices are read from. An offer is checked whenever a price is recorded for
        it."""
        latest = latest_prices()
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


def _filters(facts: Any, query: MarketQuery, now: datetime) -> list[ColumnElement[bool]]:
    """What an offer must be to match: each filter asked for."""
    c = facts.c
    wanted = scope_filters(facts, query)
    if query.drive_id is not None:
        wanted.append(c.drive_id == query.drive_id)
    if query.max_total_cents is not None:
        wanted.append(c.total <= query.max_total_cents)
    if query.in_stock:
        wanted.append(c.in_stock.is_(True))
    if query.recent_only:
        wanted.append(c.checked <= now)
        wanted.append(c.checked >= now - timedelta(days=query.recent_days))
    return wanted


def _lowest(
    session: Session, matching: Any, now: datetime, recent_days: int
) -> dict[str, list[str]]:
    """The offers with the lowest total, and the lowest total per terabyte, among those that
    match, in stock and checked recently."""
    eligible = select(matching).where(
        matching.c.in_stock.is_(True),
        matching.c.checked <= now,
        matching.c.checked >= now - timedelta(days=recent_days),
    )

    def least(name: str) -> list[str]:
        chosen = eligible.subquery()
        lowest = select(func.min(chosen.c[name])).scalar_subquery()
        return sorted(
            str(offer_id)
            for offer_id in session.scalars(select(chosen.c.id).where(chosen.c[name] == lowest))
        )

    return {"total": least("total"), "unit": least("per_tb")}


def _filter_options(
    session: Session, facts: Any, query: MarketQuery, now: datetime
) -> dict[str, list[dict[str, Any]]]:
    """Every brand, capacity and condition there are drives in, with how many drives choosing it
    would give: with the search and every other filter as asked, but not its own group's, so
    another of the group can be chosen instead. Brands with most drives in the catalogue first
    and unknown last, capacities smallest first, conditions in their usual order."""

    def drives_by(value: Any, without: str | None = None) -> dict[Any, int]:
        wanted = (
            [] if without is None else _filters(facts, query.model_copy(update={without: []}), now)
        )
        rows = session.execute(
            select(value.label("value"), func.count(func.distinct(facts.c.drive_id)))
            .where(*wanted)
            .group_by(value)
        ).tuples()
        return dict(rows.all())

    brand = func.coalesce(facts.c.brand, UNKNOWN)
    catalogue = {
        "brands": drives_by(brand),
        "capacities": drives_by(facts.c.capacity_gb),
        "conditions": drives_by(facts.c.condition),
    }
    brands = drives_by(brand, "brand")
    capacities = drives_by(facts.c.capacity_gb, "capacity")
    conditions = drives_by(facts.c.condition, "condition")
    every = catalogue["brands"]
    known = sorted((b for b in every if b != UNKNOWN), key=lambda b: (-every[b], b))
    return {
        "brands": [
            {"value": b, "drives": brands.get(b, 0)}
            for b in [*known, *([UNKNOWN] if UNKNOWN in every else [])]
        ],
        "capacities": [
            {"value": size, "drives": capacities.get(size, 0)}
            for size in sorted(catalogue["capacities"])
        ],
        "conditions": [
            {"value": condition, "drives": conditions.get(condition, 0)}
            for condition in CONDITIONS
            if condition in catalogue["conditions"]
        ],
    }
