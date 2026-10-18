"""What the API reads of the catalog: drives a page at a time, a drive and its offers, offers,
prices, the Review queue and the condition rules. Every read is one snapshot, so the queries it
takes describe one moment; filtering, ordering and paging are done by the database. The helpers
at the end read offers on a session already open, for the repository too."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Numeric, case, cast, func, literal_column, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement, Select

from disktracker.catalog.models import (
    ConditionRule,
    Drive,
    MpnAlias,
    Offer,
    Price,
    ReviewItem,
)
from disktracker.catalog.schemas import DriveQuery, DriveScope
from disktracker.catalog.views import drive_view, price_view, review_item_view, summary_view
from disktracker.collection.models import Source
from disktracker.database import SessionFactory, columns
from disktracker.errors import DriveNotFound, OfferNotFound

CONDITIONS = ("new", "manufacturer_recertified", "refurbished", "used")
UNKNOWN = "unknown"
SCALAR_SPECIFICATIONS = ("media_type", "form_factor", "interface", "recording_type")


class CatalogQueries:
    def __init__(self, snapshot_factory: SessionFactory) -> None:
        self.snapshot_factory = snapshot_factory

    # Drives, a page at a time.

    def drive_page(self, query: DriveQuery, now: datetime) -> dict[str, Any]:
        """The drives with an offer that matches, a page of them, each shown by its cheapest
        matching offer in stock (else its cheapest matching offer), drives in stock first, then
        in the order asked for; with what is said of every match, the filter options of every
        drive, and for each drive on the page the prices its range is drawn from: those of every
        offer of it in the condition it is shown in, in effect from range_days ago to now."""
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
            sold_out = 0
            if query.in_stock:
                any_stock = query.model_copy(update={"in_stock": False})
                everything = select(facts.c.drive_id).where(*_filters(facts, any_stock, now))
                drives = session.scalar(
                    select(func.count(func.distinct(everything.subquery().c.drive_id)))
                )
                sold_out = (drives or 0) - total
            page_drives = [row.drive_id for row in page]
            own = _summaries(
                session,
                select(Offer)
                .where(
                    Offer.id.in_(select(matching.c.id).where(matching.c.drive_id.in_(page_drives)))
                )
                .order_by(Offer.title, Offer.id),
            )
            # Every offer of each drive on the page in the condition it is shown in.
            kin = (
                _summaries(
                    session,
                    select(Offer)
                    .where(
                        func.row(Offer.drive_id, Offer.condition).in_(
                            [func.row(row.drive_id, row.condition) for row in page]
                        )
                    )
                    .order_by(Offer.title, Offer.id),
                )
                if page
                else []
            )
            windows = _windows(
                session,
                [UUID(offer["id"]) for offer in kin],
                now - timedelta(days=query.range_days),
            )
            return {
                "items": [_row(row, own, kin, windows) for row in page],
                "total": total,
                "offers": offers,
                "sold_out": sold_out,
                "limit": query.limit,
                "offset": query.offset,
                "as_of": now,
                "lowest": _lowest(session, matching, now, query.recent_days),
                "filter_options": _filter_options(session, facts, query, now),
            }

    def drive_detail(self, drive_id: UUID, since: datetime) -> dict[str, Any]:
        """A drive with every offer of it, each offer's prices in effect from a moment on, and
        when it was last checked: what the range of each condition is drawn from."""
        with self.snapshot_factory() as session:
            drive = session.get(Drive, drive_id)
            if drive is None:
                raise DriveNotFound()
            chosen = select(Offer).where(Offer.drive_id == drive_id).order_by(Offer.title, Offer.id)
            offers = _summaries(session, chosen)
            windows = _windows(session, [UUID(offer["id"]) for offer in offers], since)
            return {
                "drive": drive_view(drive, aliases_of(session, drive_id)),
                "offers": offers,
                "kin": [
                    (offer["condition"], windows[offer["id"]],
                     datetime.fromisoformat(offer["last_checked_at"]))
                    for offer in offers
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
            return _summaries(session, chosen)

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
                for offer in _summaries(session, select(Offer).where(Offer.id.in_(ids)))
            }
            return [found[str(offer_id)] for offer_id in ids]

    def offer(self, offer_id: UUID) -> dict[str, Any]:
        with self.snapshot_factory() as session:
            return offer_with_history(session, offer_id)

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
            wanted.append((Price.observed_at >= since) | Price.id.in_(_holding(offers, since)))
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


def _latest() -> Any:
    """Each offer's latest price."""
    return (
        select(Price)
        .distinct(Price.offer_id)
        .order_by(
            Price.offer_id, Price.observed_at.desc(), Price.entered_at.desc(), Price.id.desc()
        )
        .subquery()
    )


# The one rule for what counts in a ranking, a distribution or a trend: every offer but those held
# while a person settles what their page is (catalog.models.Offer.held_reason).
COUNTED = Offer.held_reason.is_(None)


def offer_facts() -> Select[Any]:
    """One row for each offer that counts (COUNTED): what it is filtered, grouped and ordered by. Its total and
    total per terabyte are as its latest price gives them, to the cent; it was checked when it
    was last priced, or later; its names are its title, MPN, its drive's other MPNs and who sells
    it, as search reads them."""
    latest = _latest()
    aliases = (
        select(
            MpnAlias.drive_id,
            func.string_agg(
                MpnAlias.alias, aggregate_order_by(literal_column("' '"), MpnAlias.alias)
            ).label("aliases"),
        )
        .group_by(MpnAlias.drive_id)
        .subquery()
    )
    total = latest.c.item_price_cents + func.coalesce(latest.c.shipping_cents, 0)
    seller = case((Offer.store == "other", Offer.seller), else_=Source.name)
    return (
        select(
            Offer.id,
            Offer.drive_id,
            Offer.condition,
            Offer.store,
            latest.c.in_stock,
            latest.c.acquisition_method.label("provenance"),
            total.label("total"),
            func.round(cast(total, Numeric) * 10 / Drive.capacity_gb, 2).label("per_tb"),
            func.greatest(
                latest.c.observed_at, func.coalesce(Offer.last_checked_at, latest.c.observed_at)
            ).label("checked"),
            func.concat_ws(" ", Offer.title, Offer.mpn, aliases.c.aliases, seller).label("names"),
            Drive.capacity_gb,
            Drive.brand,
            Drive.specifications,
        )
        .join(latest, latest.c.listing_id == Offer.id)
        .join(Drive, Drive.id == Offer.drive_id)
        .join(Source, Source.key == Offer.store)
        .outerjoin(aliases, aliases.c.drive_id == Offer.drive_id)
        .where(COUNTED)
    )


def _filters(facts: Any, query: DriveQuery, now: datetime) -> list[ColumnElement[bool]]:
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


def scope_filters(facts: Any, query: DriveScope) -> list[ColumnElement[bool]]:
    """What an offer (a row of offer_facts) must be to be of the drives asked for. Unknown is a
    value of every specification, and an empty list of intended uses is an unknown one."""
    c = facts.c
    wanted: list[ColumnElement[bool]] = []
    words = query.q.strip()
    if words:
        escaped = words.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        wanted.append(c.names.ilike(f"%{escaped}%", escape="\\"))
    if query.brand:
        wanted.append(func.coalesce(c.brand, UNKNOWN).in_(query.brand))
    if query.capacity:
        wanted.append(c.capacity_gb.in_(query.capacity))
    if query.condition:
        wanted.append(c.condition.in_(query.condition))
    if query.store:
        wanted.append(c.store.in_(query.store))
    for key in SCALAR_SPECIFICATIONS:
        value = getattr(query, key)
        if value is not None:
            wanted.append(func.coalesce(c.specifications[key].astext, UNKNOWN) == value)
    if query.intended_use is not None:
        uses = c.specifications["intended_use"]
        if query.intended_use == UNKNOWN:
            wanted.append(func.coalesce(func.jsonb_array_length(uses), 0) == 0)
        else:
            wanted.append(uses.contains([query.intended_use]))
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
    session: Session, facts: Any, query: DriveQuery, now: datetime
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


def _holding(offers: Any, since: datetime) -> Select[Any]:
    """The price each of these offers had as a moment came: its last one recorded before it."""
    return (
        select(Price.id)
        .where(Price.offer_id.in_(offers), Price.observed_at < since)
        .distinct(Price.offer_id)
        .order_by(
            Price.offer_id, Price.observed_at.desc(), Price.entered_at.desc(), Price.id.desc()
        )
    )


def _windows(
    session: Session, offer_ids: Sequence[UUID], since: datetime
) -> dict[str, list[dict[str, Any]]]:
    """The prices of these offers in effect from a moment on, oldest first, by offer."""
    found: dict[str, list[dict[str, Any]]] = {str(offer_id): [] for offer_id in offer_ids}
    if not offer_ids:
        return found
    for price in session.scalars(
        select(Price)
        .where(
            Price.offer_id.in_(offer_ids),
            (Price.observed_at >= since) | Price.id.in_(_holding(offer_ids, since)),
        )
        .order_by(Price.observed_at, Price.entered_at, Price.id)
    ):
        found[str(price.offer_id)].append(columns(price))
    return found


def _row(
    page_row: Any,
    own: list[dict[str, Any]],
    kin: list[dict[str, Any]],
    windows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """A drive as the list shows it: its matching offers, the one it is shown by, and the prices
    of every offer of it in that one's condition, each with when the offer was last checked."""
    drive_id, shown_id, condition = str(page_row.drive_id), str(page_row.id), page_row.condition
    offers = [offer for offer in own if offer["drive"]["id"] == drive_id]
    shown = next(offer for offer in offers if offer["id"] == shown_id)
    return {
        "key": f"drive:{drive_id}",
        "drive": shown["drive"],
        "representative": shown,
        "offers": offers,
        "kin": [
            (windows[offer["id"]], datetime.fromisoformat(offer["last_checked_at"]))
            for offer in kin
            if offer["drive"]["id"] == drive_id and offer["condition"] == condition
        ],
    }


def _summaries(session: Session, chosen: Select[Any]) -> list[dict[str, Any]]:
    """The chosen offers with their latest price, in a fixed number of queries."""
    offers = list(session.scalars(chosen))
    ids = [offer.id for offer in offers]
    drive_ids = {offer.drive_id for offer in offers}
    latest = {
        price.offer_id: price
        for price in session.scalars(
            select(Price)
            .where(Price.offer_id.in_(ids))
            .distinct(Price.offer_id)
            .order_by(
                Price.offer_id, Price.observed_at.desc(), Price.entered_at.desc(), Price.id.desc()
            )
        )
    }
    drives = {
        drive.id: drive for drive in session.scalars(select(Drive).where(Drive.id.in_(drive_ids)))
    }
    names = dict(session.execute(select(Source.key, Source.name)).tuples().all())
    aliases: dict[UUID, list[str]] = {}
    for alias in session.scalars(
        select(MpnAlias).where(MpnAlias.drive_id.in_(drive_ids)).order_by(MpnAlias.alias)
    ):
        aliases.setdefault(alias.drive_id, []).append(alias.alias)
    return [
        summary_view(
            offer,
            drives[offer.drive_id],
            aliases.get(offer.drive_id, []),
            latest[offer.id],
            names[offer.store],
            offer.held_reason,
        )
        for offer in offers
    ]


def offer_with_history(session: Session, offer_id: UUID) -> dict[str, Any]:
    """One offer with every price it has had, oldest first."""
    [offer] = _summaries(session, select(Offer).where(Offer.id == offer_id)) or [None]
    if offer is None:
        raise OfferNotFound()
    prices = session.scalars(
        select(Price)
        .where(Price.offer_id == offer_id)
        .order_by(Price.observed_at, Price.entered_at, Price.id)
    )
    return {**offer, "observations": [price_view(price, offer["capacity_gb"]) for price in prices]}


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
