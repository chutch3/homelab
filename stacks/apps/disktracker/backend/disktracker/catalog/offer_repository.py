"""Offers, their prices, and the receipts that keep a price saved twice from being recorded
twice. Each method works on the session of the operation that calls it and never commits: the
operation decides what is kept together.

Recording a price is only that: for a drive that already exists, an offer is found or made, and
the price kept or counted as a check. It never makes a drive, changes one, names its other MPNs,
holds or releases an offer, or decides what a store page is; those are the callers'."""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from disktracker.catalog.models import Drive, Offer, Price, Receipt
from disktracker.catalog.rules import combined_offer, replayed, unchanged, with_carried_price
from disktracker.collection.models import Source
from disktracker.database import columns
from disktracker.errors import OfferNotFound, UnknownStore
from disktracker.facts import LATEST_FIRST

OFFER_IDENTITY = (Offer.drive_id, Offer.store, Offer.seller, Offer.condition)


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
        identity = {"drive_id": drive_id, "store": store, "seller": seller, "condition": condition}
        session.execute(
            pg_insert(Offer)
            .values(id=self.next_id(), **identity, title=title or mpn, url=url)
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
            select(Price).where(Price.offer_id == offer_id).order_by(*LATEST_FIRST).limit(1)
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

    def claim(self, session: Session, request_id: UUID, fingerprint: str) -> dict[str, Any] | None:
        """Take a save key for this submission, held until the operation ends: None when it is
        new, or what was answered when it was used before (refused for another submission)."""
        claimed = session.scalar(
            pg_insert(Receipt)
            .values(id=request_id, fingerprint=fingerprint)
            .on_conflict_do_nothing(index_elements=[Receipt.id])
            .returning(Receipt.id)
        )
        if claimed is not None:
            return None
        saved = session.get_one(Receipt, request_id)
        return replayed(saved.result, saved.fingerprint, fingerprint)

    def answer(self, session: Session, request_id: UUID, result: dict[str, Any]) -> None:
        """Keep what a save key's submission was answered, to answer it again."""
        session.execute(update(Receipt).where(Receipt.id == request_id).values(result=result))

    def lock(self, session: Session, offer_id: UUID) -> None:
        """Hold an existing offer against other changes until the operation ends."""
        if session.scalar(select(Offer.id).where(Offer.id == offer_id).with_for_update()) is None:
            raise OfferNotFound()

    def hold(
        self,
        session: Session,
        *,
        drive_id: UUID,
        store: str,
        seller: str,
        condition: str,
        reason: str,
    ) -> None:
        """Hold the offer of this drive at this store, from this seller, in this condition, if it
        exists: in no ranking, distribution or trend until a person settles it. No other offer
        of its page is held by it."""
        session.execute(
            update(Offer)
            .where(
                Offer.drive_id == drive_id,
                Offer.store == store,
                Offer.seller == seller,
                Offer.condition == condition,
            )
            .values(held_reason=reason)
        )

    def release(self, session: Session, offer_id: UUID) -> None:
        """Count an offer in rankings, distributions and trends again: only this one, whatever
        else shares its store page."""
        session.execute(
            update(Offer)
            .where(Offer.id == offer_id, Offer.held_reason.is_not(None))
            .values(held_reason=None)
        )

    def consolidate(
        self, session: Session, source_id: UUID, target_id: UUID
    ) -> list[tuple[UUID, UUID]]:
        """Move the source drive's offers to the target drive, held against other changes until
        the operation ends. One the target already has an offer of at the same store, from the
        same seller, in the same condition is combined into it: its prices (their ids kept) are
        that offer's, which stays held if either was and is last checked when either was; then it
        is gone. The pairs combined, absorbed offer first."""
        offers = session.scalars(
            select(Offer)
            .where(Offer.drive_id.in_([source_id, target_id]))
            .order_by(Offer.id)
            .with_for_update()
        ).all()
        kept = {(o.store, o.seller, o.condition): o for o in offers if o.drive_id == target_id}
        combined = []
        for absorbed in (o for o in offers if o.drive_id == source_id):
            survivor = kept.get((absorbed.store, absorbed.seller, absorbed.condition))
            if survivor is None:
                session.execute(
                    update(Offer).where(Offer.id == absorbed.id).values(drive_id=target_id)
                )
                continue
            session.execute(
                update(Price).where(Price.offer_id == absorbed.id).values(offer_id=survivor.id)
            )
            session.execute(
                update(Offer)
                .where(Offer.id == survivor.id)
                .values(**combined_offer(columns(survivor), columns(absorbed)))
            )
            session.execute(delete(Offer).where(Offer.id == absorbed.id))
            combined.append((absorbed.id, survivor.id))
        return combined
