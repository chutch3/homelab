"""Offers and their prices. Each method works on the session of the operation that calls it and
never commits: the operation decides what is kept together.

Recording a price is only that: for a drive that already exists, an offer is found or made, and
the price kept or counted as a check. It never makes a drive, changes one, names its other MPNs,
holds or releases an offer, or decides what a store page is; those are the callers'."""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from disktracker.catalog.models import Drive, Offer, Price
from disktracker.catalog.rules import unchanged, with_carried_price
from disktracker.collection.models import Source
from disktracker.database import columns
from disktracker.errors import UnknownStore

OFFER_IDENTITY = (Offer.mpn, Offer.store, Offer.seller, Offer.condition)


class OfferRepository:
    def __init__(self, now: Callable[[], datetime], next_id: Callable[[], UUID]) -> None:
        self.now, self.next_id = now, next_id

    def offer_for(
        self,
        session: Session,
        *,
        drive_id: UUID,
        store: str,
        seller: str,
        condition: str,
        title: str | None,
        url: str | None,
    ) -> UUID:
        """The offer of this drive (one that exists) at this store, from this seller, in this
        condition, held against other changes until the operation ends; made when it is new, at a
        store that is known, named by its title or else its drive's MPN."""
        if session.scalar(select(Source.key).where(Source.key == store)) is None:
            raise UnknownStore()
        mpn = session.scalars(select(Drive.mpn).where(Drive.id == drive_id)).one()
        identity = {"mpn": mpn, "store": store, "seller": seller, "condition": condition}
        session.execute(
            pg_insert(Offer)
            .values(id=self.next_id(), drive_id=drive_id, **identity, title=title or mpn, url=url)
            .on_conflict_do_nothing(index_elements=[column.key for column in OFFER_IDENTITY])
        )
        offer_id: UUID = session.scalars(
            select(Offer.id)
            .where(*(getattr(Offer, key) == value for key, value in identity.items()))
            .with_for_update()
        ).one()
        return offer_id

    def record(
        self, session: Session, offer_id: UUID, price: dict[str, Any], provenance: str
    ) -> UUID | None:
        """Keep a price for an offer: the price made, or None when it was the same as the
        offer's latest, and so only counted as a check. A price sold out carries the latest
        price on (catalog.rules.with_carried_price), so an offer never priced cannot record
        one."""
        entered_at = self.now()
        observed_at = price["observed_at"] or entered_at
        latest = session.scalars(
            select(Price)
            .where(Price.offer_id == offer_id)
            .order_by(Price.observed_at.desc(), Price.entered_at.desc())
            .limit(1)
        ).first()
        before = None if latest is None else columns(latest)
        values = with_carried_price(
            {key: value for key, value in price.items() if key != "observed_at"}, before
        )
        if unchanged(values, observed_at, before):
            session.execute(
                update(Offer)
                .where(Offer.id == offer_id)
                .values(last_checked_at=func.greatest(Offer.last_checked_at, observed_at))
            )
            return None
        price_id = self.next_id()
        session.add(
            Price(
                **values,
                id=price_id,
                offer_id=offer_id,
                observed_at=observed_at,
                entered_at=entered_at,
                provenance=provenance,
            )
        )
        session.flush()
        return price_id
