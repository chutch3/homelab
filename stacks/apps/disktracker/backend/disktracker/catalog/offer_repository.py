"""Offers, their prices, and the receipts that keep a price saved twice from being recorded
twice: written, and read as offers with their latest price or their history. Each method works on
the session of the operation that calls it and never commits: the operation decides what is kept
together.

Recording a price is only that: for a drive that already exists, an offer is found or made, and
the price kept or counted as a check. It never makes a drive, changes one, names its other MPNs,
holds or releases an offer, or decides what a store page is; those are the callers'."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from disktracker.catalog.models import Drive, MpnAlias, Offer, Price, Receipt
from disktracker.catalog.rules import combined_offer, replayed, unchanged, with_carried_price
from disktracker.catalog.views import price_view, summary_view
from disktracker.clock import Clock
from disktracker.collector.models import Source
from disktracker.database import columns
from disktracker.errors import OfferNotFound, UnknownStore
from disktracker.facts import LATEST_FIRST

OFFER_IDENTITY = (Offer.drive_id, Offer.store, Offer.seller, Offer.condition)


class OfferRepository:
    def __init__(self, clock: Clock) -> None:
        self.clock = clock

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
            .values(**identity, title=title or mpn, url=url)
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
        entered_at = self.clock.now()
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
        made = Price(
            **values,
            offer_id=offer_id,
            observed_at=observed_at,
            entered_at=entered_at,
            provenance=provenance,
        )
        session.add(made)
        session.flush()
        return made.id

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

    def edit(self, session: Session, offer_id: UUID, fields: dict[str, Any]) -> None:
        """Change what is given of an offer (one that exists), and leave the rest."""
        if fields:
            session.execute(update(Offer).where(Offer.id == offer_id).values(**fields))

    def delete(self, session: Session, offer_id: UUID) -> None:
        """An offer gone, with its prices; its drive stays."""
        session.execute(delete(Price).where(Price.offer_id == offer_id))
        session.execute(delete(Offer).where(Offer.id == offer_id))

    def offer_priced(self, session: Session, price_id: UUID) -> UUID | None:
        """The offer a price is of; None for a price that is not there."""
        return session.scalar(select(Price.offer_id).where(Price.id == price_id))

    def remove_price(self, session: Session, offer_id: UUID, price_id: UUID) -> bool:
        """A price of this offer gone: whether the offer has any price left."""
        session.execute(delete(Price).where(Price.id == price_id))
        left = select(Price.id).where(Price.offer_id == offer_id).limit(1)
        return session.scalar(left) is not None

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

    def priced(
        self, session: Session, *, drive_id: UUID, store: str, seller: str, condition: str
    ) -> bool:
        """Whether the offer of this drive at this store, from this seller, in this condition has
        a price: one a sold-out observation of it can carry on."""
        offer = select(Offer.id).where(
            Offer.drive_id == drive_id,
            Offer.store == store,
            Offer.seller == seller,
            Offer.condition == condition,
        )
        return (
            session.scalar(select(Price.id).where(Price.offer_id.in_(offer)).limit(1)) is not None
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

    # Offers and their prices, read.

    def summaries(self, session: Session, chosen: Select[Any]) -> list[dict[str, Any]]:
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
                .order_by(Price.offer_id, *LATEST_FIRST)
            )
        }
        drives = {
            drive.id: drive
            for drive in session.scalars(select(Drive).where(Drive.id.in_(drive_ids)))
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

    def listed(
        self, session: Session, store: str | None, drive_id: UUID | None
    ) -> list[dict[str, Any]]:
        """Every offer, of one store or one drive when asked, held ones too, with its latest
        price, by title."""
        chosen = select(Offer).order_by(Offer.title, Offer.id)
        if store is not None:
            chosen = chosen.where(Offer.store == store)
        if drive_id is not None:
            chosen = chosen.where(Offer.drive_id == drive_id)
        return self.summaries(session, chosen)

    def price_page(
        self,
        session: Session,
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
            {**price_view(price, capacity), "offer_id": price.offer_id} for price, capacity in found
        ]
        return items, total

    def with_history(self, session: Session, offer_id: UUID) -> dict[str, Any]:
        """One offer with every price it has had, oldest first."""
        [offer] = self.summaries(session, select(Offer).where(Offer.id == offer_id)) or [None]
        if offer is None:
            raise OfferNotFound()
        prices = session.scalars(
            select(Price)
            .where(Price.offer_id == offer_id)
            .order_by(Price.observed_at, Price.entered_at, Price.id)
        )
        return {
            **offer,
            "observations": [price_view(price, offer["capacity_gb"]) for price in prices],
        }

    def prices_since(
        self, session: Session, offer_ids: Sequence[UUID], since: datetime
    ) -> dict[UUID, list[dict[str, Any]]]:
        """The prices of these offers in effect from a moment on, oldest first, by offer."""
        found: dict[UUID, list[dict[str, Any]]] = {offer_id: [] for offer_id in offer_ids}
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
            found[price.offer_id].append(columns(price))
        return found


def _holding(offers: Any, since: datetime) -> Select[Any]:
    """The price each of these offers had as a moment came: its last one recorded before it."""
    return (
        select(Price.id)
        .where(Price.offer_id.in_(offers), Price.observed_at < since)
        .distinct(Price.offer_id)
        .order_by(Price.offer_id, *LATEST_FIRST)
    )
