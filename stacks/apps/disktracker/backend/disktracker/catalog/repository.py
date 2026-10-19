"""The catalog's writes, exercised with real-database integration tests. Every operation opens
its own session, does all of its work there, and commits once: a price with its receipt, a
review decision with what it records, a merge of drives, are each kept whole or not at all. What
an operation returns is plain data, complete before its session closes. What to do at each turn
is decided by the catalog's rules; what the API reads is in catalog.queries."""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from disktracker.catalog.drive_repository import hold_mpn
from disktracker.catalog.models import (
    ConditionRule,
    Drive,
    MpnAlias,
    Offer,
    Price,
    Receipt,
    ReviewDecision,
    ReviewItem,
    ScrapedMatch,
)
from disktracker.catalog.queries import aliases_of, canonical_mpn, offer_with_history
from disktracker.catalog.rules import (
    as_decided,
    capacity_label,
    decided_again,
    doubt,
    fill_unknown,
    merge_plan,
    missing_detail,
    new_aliases,
    queue_reason,
    queued_fields,
    replayed,
    unchanged,
    with_carried_price,
)
from disktracker.catalog.schemas import ObservationInput, PriceInput, Specifications
from disktracker.catalog.schemas import ReviewDecision as Decision
from disktracker.catalog.views import drive_view
from disktracker.collection.models import Source
from disktracker.database import SessionFactory, by_column, columns
from disktracker.errors import (
    AliasConflict,
    CapacityConflict,
    CapacityRequired,
    DriveNotFound,
    OfferNotFound,
    PriceRequired,
    ReviewItemNotFound,
    UnknownStore,
)

OFFER_IDENTITY = (Offer.mpn, Offer.store, Offer.seller, Offer.condition)


class CatalogRepository:
    def __init__(
        self,
        session_factory: SessionFactory,
        now: Callable[[], datetime],
        next_id: Callable[[], UUID],
    ) -> None:
        self.session_factory, self.now, self.next_id = session_factory, now, next_id

    # Recording a price.

    def record_price(
        self, entry: PriceInput, price: dict[str, Any], request_id: UUID, fingerprint: str
    ) -> dict[str, Any]:
        """Record a submitted price, queue it for review, or ignore it, with the receipt for its
        save key, all in one transaction. A save key already used is answered from its receipt
        without doing the work again; one used for a different request is refused."""
        with self.session_factory() as session:
            claimed = session.scalar(
                pg_insert(Receipt)
                .values(id=request_id, fingerprint=fingerprint)
                .on_conflict_do_nothing(index_elements=[Receipt.id])
                .returning(Receipt.id)
            )
            if claimed is None:
                saved = session.get_one(Receipt, request_id)
                return replayed(saved.result, saved.fingerprint, fingerprint)
            result = self._submit(session, entry, price)
            session.execute(update(Receipt).where(Receipt.id == request_id).values(result=result))
            session.commit()
            return result

    def _submit(self, session: Session, entry: PriceInput, price: dict[str, Any]) -> dict[str, Any]:
        found = _identity(session, entry)
        collected = entry.provenance == "collected"
        identity: dict[str, Any] | None = found
        decided = None
        if collected and entry.url is not None:
            decided = session.get(ScrapedMatch, (found["store"], str(entry.url)))
            identity = as_decided(found, None if decided is None else columns(decided))
        if identity is None:
            return {"status": "ignored"}
        reason = missing_detail(identity["mpn"], identity["condition"])
        if reason is None and collected and decided is None:
            # What a person has said an offer is, or entered, is taken as said. Its capacity is
            # what it is recorded under: the offer's, or else its drive's.
            capacity = entry.capacity_gb or session.scalar(
                select(Drive.capacity_gb).where(
                    Drive.mpn == canonical_mpn(session, identity["mpn"])
                )
            )
            reason = doubt(entry.title, capacity, identity["mpn"])
            if reason is not None and entry.url is not None:
                # What was recorded of its page counts for nothing until a person settles it.
                session.execute(
                    update(Offer)
                    .where(Offer.store == identity["store"], Offer.url == str(entry.url))
                    .values(held_reason=reason)
                )
        if reason is not None:
            return self._queue(session, entry, identity, price, reason)
        try:
            # Held apart, so that what it wrote before finding it cannot be recorded is undone.
            with session.begin_nested():
                offer_id, price_id = self._record(
                    session,
                    identity,
                    price,
                    # Once a person has said what a page is, the capacity of its drive stands,
                    # whatever the page goes on saying.
                    capacity_gb=entry.capacity_gb if decided is None else None,
                    title=entry.title,
                    url=str(entry.url) if entry.url else None,
                    provenance=entry.provenance,
                )
        except PriceRequired:
            if not collected:
                raise
            # Only a sold-out offer lacks a price, and one never seen in stock has no real price
            # to track yet.
            return {"status": "ignored"}
        except (CapacityConflict, CapacityRequired) as error:
            if entry.on_unmatched != "queue":
                raise
            return self._queue(session, entry, identity, price, queue_reason(error))
        self._describe_drive(session, offer_id, entry)
        if collected and entry.url is not None:
            # An offer that is recorded now is no longer waiting for review.
            session.execute(
                delete(ReviewItem).where(
                    ReviewItem.store == identity["store"], ReviewItem.url == str(entry.url)
                )
            )
        return {
            "status": "recorded",
            "offer_id": str(offer_id),
            "price_id": str(price_id) if price_id else None,
        }

    def _record(
        self,
        session: Session,
        identity: dict[str, Any],
        price: dict[str, Any],
        *,
        capacity_gb: int | None,
        title: str | None,
        url: str | None,
        provenance: str,
    ) -> tuple[UUID, UUID | None]:
        """Keep a price for the offer so identified, creating the offer and its drive when they
        are new. The offer, and the price made: None when it only counted as a check."""
        if not _store_known(session, identity["store"]):
            raise UnknownStore()
        mpn = canonical_mpn(session, identity["mpn"])
        drive_id = self._resolve_drive(session, mpn, capacity_gb)
        offer_id = self._ensure_offer(
            session, {**identity, "mpn": mpn}, drive_id, title or mpn, url
        )
        # Recorded, it is not in doubt: read without doubt, or settled by a person.
        session.execute(
            update(Offer)
            .where(Offer.id == offer_id, Offer.held_reason.is_not(None))
            .values(held_reason=None)
        )
        entered_at = self.now()
        observed_at = price["observed_at"] or entered_at
        latest = session.scalars(
            select(Price)
            .where(Price.offer_id == offer_id)
            .order_by(Price.observed_at.desc(), Price.entered_at.desc())
            .limit(1)
        ).first()
        values = with_carried_price(
            {key: value for key, value in price.items() if key != "observed_at"},
            None if latest is None else columns(latest),
        )
        if unchanged(values, observed_at, None if latest is None else columns(latest)):
            session.execute(
                update(Offer)
                .where(Offer.id == offer_id)
                .values(last_checked_at=func.greatest(Offer.last_checked_at, observed_at))
            )
            return offer_id, None
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
        return offer_id, price_id

    def _resolve_drive(self, session: Session, mpn: str, capacity: int | None) -> UUID:
        """The drive for this MPN, held against other changes; created, with unknown
        specifications, on first sight."""
        find = select(Drive).where(Drive.mpn == mpn).with_for_update()
        drive = session.scalars(find).first()
        if drive is None:
            if capacity is None:
                raise CapacityRequired()
            session.execute(
                pg_insert(Drive)
                .values(id=self.next_id(), mpn=mpn, capacity_gb=capacity)
                .on_conflict_do_nothing(index_elements=[Drive.mpn])
            )
            drive = session.scalars(find).one()
        if capacity is not None and capacity != drive.capacity_gb:
            raise CapacityConflict(
                f"MPN {mpn} is recorded as {capacity_label(drive.capacity_gb)}."
                " Edit the drive's specifications to change its capacity."
            )
        return drive.id

    def _ensure_offer(
        self,
        session: Session,
        identity: dict[str, Any],
        drive_id: UUID,
        title: str,
        url: str | None,
    ) -> UUID:
        """The offer with this identity, held against other changes; created when it is new."""
        session.execute(
            pg_insert(Offer)
            .values(id=self.next_id(), drive_id=drive_id, **identity, title=title, url=url)
            .on_conflict_do_nothing(index_elements=[column.key for column in OFFER_IDENTITY])
        )
        offer_id: UUID = session.scalars(
            select(Offer.id)
            .where(*(getattr(Offer, key) == value for key, value in identity.items()))
            .with_for_update()
        ).one()
        return offer_id

    def _describe_drive(self, session: Session, offer_id: UUID, entry: PriceInput) -> None:
        """Take what a submitter says of an offer's drive: its specifications and brand where
        nobody has entered them, and the other MPNs it goes by."""
        if entry.specifications is None and entry.brand is None and not entry.aliases:
            return
        drive = session.scalars(
            select(Drive)
            .join(Offer, Offer.drive_id == Drive.id)
            .where(Offer.id == offer_id)
            .with_for_update(of=Drive)
        ).one()
        if entry.specifications is not None:
            filled = fill_unknown(
                Specifications.model_validate(drive.specifications).model_dump(mode="json"),
                entry.specifications.model_dump(mode="json"),
            )
            session.execute(update(Drive).where(Drive.id == drive.id).values(specifications=filled))
        if entry.brand is not None:
            # A source's brand only names a drive nobody has named yet.
            session.execute(
                update(Drive)
                .where(Drive.id == drive.id, Drive.brand.is_(None))
                .values(brand=entry.brand)
            )
        for alias in new_aliases(entry.aliases, drive.mpn, aliases_of(session, drive.id)):
            try:
                _add_alias(session, drive.id, alias)
            except AliasConflict:
                # Already another drive's alias; leave that for a person to sort out.
                continue

    def _queue(
        self,
        session: Session,
        entry: PriceInput,
        identity: dict[str, Any],
        price: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        seen_at = entry.observed_at or self.now()
        fields = {
            **queued_fields(entry.model_dump(), identity, price, reason),
            "last_seen_at": seen_at,
        }
        # Kept in place of what was kept of the same store page before.
        table = ReviewItem.__table__
        item_id: UUID = session.scalars(
            pg_insert(table)
            .values(
                by_column(ReviewItem, {"id": self.next_id(), "first_seen_at": seen_at, **fields})
            )
            .on_conflict_do_update(
                index_elements=[table.c.source, table.c.url], set_=by_column(ReviewItem, fields)
            )
            .returning(table.c.id)
        ).one()
        return {"status": "queued", "review_item_id": str(item_id)}

    # The Review queue, and deciding what a queued offer is.

    def decide(self, item_id: UUID, decision: Decision) -> dict[str, Any]:
        """Decide what a review item is and remember it for later prices of the same store page:
        the decision, what it records and the item leaving the queue are kept together. The same
        decision sent again gets the first answer and changes nothing; a different one is
        refused."""
        body = decision.model_dump(mode="json")
        with self.session_factory() as session:
            claimed = session.scalar(
                pg_insert(ReviewDecision)
                .values(id=item_id, decision=body)
                .on_conflict_do_nothing(index_elements=[ReviewDecision.id])
                .returning(ReviewDecision.id)
            )
            if claimed is None:
                earlier = session.get_one(ReviewDecision, item_id)
                return decided_again(earlier.decision, earlier.result, body)
            item = session.get(ReviewItem, item_id)
            if item is None:
                raise ReviewItemNotFound()
            queued = columns(item)
            session.execute(delete(ReviewItem).where(ReviewItem.id == item_id))
            if decision.decision == "ignore":
                _remember(session, queued, mpn=None, condition=None, ignored=True)
                result: dict[str, Any] = {"status": "ignored", "offer_id": None}
            else:
                price = ObservationInput.model_validate(
                    {key: queued[key] for key in ("item_price_cents", "shipping_cents", "in_stock")}
                    | {"observed_at": queued["last_seen_at"]}
                )
                known = session.scalars(
                    select(Drive)
                    .where(Drive.mpn == canonical_mpn(session, decision.mpn))
                    .with_for_update()
                ).first()
                if decision.correct_drive and known is not None:
                    session.execute(
                        update(Drive)
                        .where(Drive.id == known.id)
                        .values(capacity_gb=decision.capacity_gb)
                    )
                # Left unsaid, a drive already recorded keeps its capacity, whatever the offer
                # said; a new one takes the offer's.
                capacity = decision.capacity_gb
                if capacity is None and known is None:
                    capacity = queued["capacity_gb"]
                offer_id, _ = self._record(
                    session,
                    {
                        "mpn": decision.mpn,
                        "store": queued["store"],
                        "seller": queued["seller"],
                        "condition": decision.condition,
                    },
                    price.model_dump(),
                    capacity_gb=capacity,
                    title=queued["title"],
                    url=queued["url"],
                    provenance=queued["provenance"],
                )
                _remember(
                    session, queued, mpn=decision.mpn, condition=decision.condition, ignored=False
                )
                result = {"status": "matched", "offer_id": str(offer_id)}
            session.execute(
                update(ReviewDecision).where(ReviewDecision.id == item_id).values(result=result)
            )
            session.commit()
            return result

    # Drives and the MPNs they go by.

    def add_alias(self, drive_id: UUID, alias: str) -> dict[str, Any]:
        """Declare another MPN for a drive, merging in any drive already recorded under it."""
        with self.session_factory() as session:
            drive = _add_alias(session, drive_id, alias)
            session.commit()
            return drive_view(drive, aliases_of(session, drive_id))

    def edit_drive(
        self, drive_id: UUID, values: dict[str, Any], specifications: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Change what is given of a drive, its specifications one by one, and leave the rest."""
        with self.session_factory() as session:
            drive = _lock_drive(session, drive_id)
            if specifications is not None:
                values = values | {
                    "specifications": Specifications.model_validate(
                        drive.specifications | specifications
                    ).model_dump(mode="json")
                }
            if values:
                session.execute(update(Drive).where(Drive.id == drive_id).values(**values))
                session.refresh(drive)
            session.commit()
            return drive_view(drive, aliases_of(session, drive_id))

    # Offers and prices, corrected.

    def edit_offer(self, offer_id: UUID, fields: dict[str, Any]) -> dict[str, Any]:
        with self.session_factory() as session:
            _lock_offer(session, offer_id)
            if fields:
                session.execute(update(Offer).where(Offer.id == offer_id).values(**fields))
            offer = offer_with_history(session, offer_id)
            session.commit()
            return offer

    def delete_offer(self, offer_id: UUID) -> None:
        with self.session_factory() as session:
            _lock_offer(session, offer_id)
            _delete_offer(session, offer_id)
            session.commit()

    def delete_price(self, price_id: UUID) -> None:
        """Remove a price, and its offer with it when it was the offer's last. A price that is
        not there is already removed."""
        with self.session_factory() as session:
            offer_id = session.scalar(select(Price.offer_id).where(Price.id == price_id))
            if offer_id is None:
                return
            _lock_offer(session, offer_id)
            session.execute(delete(Price).where(Price.id == price_id))
            if session.scalar(select(Price.id).where(Price.offer_id == offer_id).limit(1)) is None:
                _delete_offer(session, offer_id)
            session.commit()

    # The rules that read a condition from listing text.

    def replace_condition_rules(self, rules: list[dict[str, Any]]) -> None:
        with self.session_factory() as session:
            session.execute(delete(ConditionRule))
            session.add_all(
                ConditionRule(position=index, **rule) for index, rule in enumerate(rules)
            )
            session.commit()


# What the operations above share, each on the session of the operation that calls it.


def _identity(session: Session, entry: PriceInput) -> dict[str, Any]:
    """What identifies the offer a price is for: that of the offer named, held against other
    changes, or as described."""
    if entry.offer_id is not None:
        row = session.execute(
            select(*OFFER_IDENTITY).where(Offer.id == entry.offer_id).with_for_update()
        ).first()
        if row is None:
            raise OfferNotFound()
        return dict(row._mapping)
    return {
        "mpn": entry.mpn,
        "store": entry.store,
        "seller": entry.seller,
        "condition": entry.condition,
    }


def _store_known(session: Session, store: str) -> bool:
    return session.scalar(select(Source.key).where(Source.key == store)) is not None


def _lock_drive(session: Session, drive_id: UUID) -> Drive:
    drive = session.scalars(select(Drive).where(Drive.id == drive_id).with_for_update()).first()
    if drive is None:
        raise DriveNotFound()
    return drive


def _lock_offer(session: Session, offer_id: UUID) -> None:
    """Hold an offer against other changes until the transaction ends."""
    if session.scalar(select(Offer.id).where(Offer.id == offer_id).with_for_update()) is None:
        raise OfferNotFound()


def _delete_offer(session: Session, offer_id: UUID) -> None:
    session.execute(delete(Price).where(Price.offer_id == offer_id))
    session.execute(delete(Offer).where(Offer.id == offer_id))


def _add_alias(session: Session, drive_id: UUID, alias: str) -> Drive:
    """Declare another MPN for a drive; a drive recorded under it is merged in, its offers
    moving across, or combining with the matching offer, and its own aliases following."""
    hold_mpn(session, alias)
    drive = _lock_drive(session, drive_id)
    taken = session.scalar(select(MpnAlias.drive_id).where(MpnAlias.alias == alias))
    if alias == drive.mpn or taken is not None:
        raise AliasConflict(f"{alias} already identifies a drive.")
    variant = session.scalars(select(Drive).where(Drive.mpn == alias).with_for_update()).first()
    if variant is not None:
        plan = merge_plan(
            [
                columns(offer)
                for offer in session.scalars(select(Offer).where(Offer.drive_id == variant.id))
            ],
            [
                columns(offer)
                for offer in session.scalars(select(Offer).where(Offer.drive_id == drive.id))
            ],
        )
        for offer_id, twin in plan:
            if twin is None:
                session.execute(
                    update(Offer)
                    .where(Offer.id == offer_id)
                    .values(mpn=drive.mpn, drive_id=drive.id)
                )
            else:
                # Its prices join the matching offer, and it goes.
                session.execute(
                    update(Price).where(Price.offer_id == offer_id).values(offer_id=twin)
                )
                session.execute(delete(Offer).where(Offer.id == offer_id))
        session.execute(
            update(MpnAlias).where(MpnAlias.drive_id == variant.id).values(drive_id=drive.id)
        )
        session.execute(delete(Drive).where(Drive.id == variant.id))
    session.add(MpnAlias(alias=alias, drive_id=drive_id))
    session.flush()
    return drive


def _remember(session: Session, queued: dict[str, Any], **decision: Any) -> None:
    """Keep what was decided about a store page, for later collected prices of it."""
    table = ScrapedMatch.__table__
    session.execute(
        pg_insert(table)
        .values(
            by_column(ScrapedMatch, {"store": queued["store"], "url": queued["url"], **decision})
        )
        .on_conflict_do_update(index_elements=[table.c.source, table.c.url], set_=decision)
    )
