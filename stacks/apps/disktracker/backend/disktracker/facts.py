"""What the catalog and reporting both mean by an offer's facts: its latest price, whether it
counts, what it is filtered, grouped and ordered by, and which drives a page narrows to. The
definitions every read and write of them uses, so that none can mean another. They are over the
catalog's tables (disktracker.catalog.models)."""

from typing import Any

from sqlalchemy import Numeric, case, cast, func, literal_column, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.sql import ColumnElement, Select

from disktracker.catalog.models import Drive, MpnAlias, Offer, Price
from disktracker.catalog.rules import SCALAR_SPECIFICATIONS, UNKNOWN
from disktracker.catalog.schemas import DriveScope
from disktracker.collection.models import Source

# An offer's prices, latest first: the latest seen, then the latest entered, then the latest made,
# so that one of several seen and entered at one moment is the latest everywhere.
LATEST_FIRST = (Price.observed_at.desc(), Price.entered_at.desc(), Price.id.desc())

# What counts in a ranking, a distribution or a trend: every offer but those held while a person
# settles what their page is (catalog.models.Offer.held_reason). Administration, store freshness
# and an offer's own history include held offers too.
COUNTED = Offer.held_reason.is_(None)


def latest_prices() -> Any:
    """Each offer's latest price (LATEST_FIRST), one row for each."""
    return select(Price).distinct(Price.offer_id).order_by(Price.offer_id, *LATEST_FIRST).subquery()


def offer_facts() -> Select[Any]:
    """One row for each offer that counts (COUNTED), as every_offer_facts gives it."""
    return every_offer_facts().where(COUNTED)


def every_offer_facts() -> Select[Any]:
    """One row for each offer, held or not: what it is filtered, grouped and ordered by. Its total and
    total per terabyte are as its latest price gives them, to the cent; it was checked when it
    was last priced, or later; it is sold by its store, or for a one-off store by its seller; its
    names are its title, MPN, its drive's other MPNs and who sells it, as search reads them."""
    latest = latest_prices()
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
            Offer.title,
            Offer.condition,
            Offer.store,
            latest.c.in_stock,
            latest.c.acquisition_method.label("provenance"),
            total.label("total"),
            func.round(cast(total, Numeric) * 10 / Drive.capacity_gb, 2).label("per_tb"),
            func.greatest(
                latest.c.observed_at, func.coalesce(Offer.last_checked_at, latest.c.observed_at)
            ).label("checked"),
            func.concat_ws(" ", Offer.title, Drive.mpn, aliases.c.aliases, seller).label("names"),
            seller.label("sold_by"),
            Drive.capacity_gb,
            Drive.brand,
            Drive.specifications,
        )
        .join(latest, latest.c.listing_id == Offer.id)
        .join(Drive, Drive.id == Offer.drive_id)
        .join(Source, Source.key == Offer.store)
        .outerjoin(aliases, aliases.c.drive_id == Offer.drive_id)
    )


def escaped(words: str) -> str:
    """Words to look for as they are typed, in a LIKE pattern escaped with a backslash."""
    return words.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def named_by(facts: Any, words: str) -> ColumnElement[bool]:
    """Whether an offer (a row of offer_facts) goes by a name containing the words, as typed."""
    return facts.c.names.ilike(f"%{escaped(words)}%", escape="\\")


def scope_filters(facts: Any, query: DriveScope) -> list[ColumnElement[bool]]:
    """What an offer (a row of offer_facts) must be to be of the drives asked for. Unknown is a
    value of every specification, and an empty list of intended uses is an unknown one."""
    c = facts.c
    wanted: list[ColumnElement[bool]] = []
    words = query.q.strip()
    if words:
        wanted.append(named_by(facts, words))
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
