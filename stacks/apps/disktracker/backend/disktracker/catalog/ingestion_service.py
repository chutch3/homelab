"""Taking in one observation of an offer described rather than named: what its listing has been
decided to be, whether it can be taken as it reads, the drive it is of (registered when new and
the evidence is enough), the price recorded through the one price writer, and what its page says
of the drive; or it waits for review, or is ignored. One piece of work with its save key: all of
it is kept, or none."""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.price_service import fingerprint, observation, recorded
from disktracker.catalog.review_repository import Listing, ReviewRepository
from disktracker.catalog.rules import (
    as_decided,
    doubt,
    missing_detail,
    queue_reason,
    queued_fields,
)
from disktracker.catalog.schemas import PriceInput
from disktracker.database import SessionFactory
from disktracker.errors import CapacityConflict, CapacityRequired, PriceRequired


class _NamesAnotherDrive(Exception):
    """The page named an MPN another drive goes by: nothing it said is taken."""

    def __init__(self, mpn: str, drive_id: UUID) -> None:
        super().__init__(mpn)
        self.mpn, self.drive_id = mpn, drive_id


class IngestionService:
    def __init__(
        self,
        session_factory: SessionFactory,
        drives: DriveRepository,
        offers: OfferRepository,
        reviews: ReviewRepository,
        now: Callable[[], datetime],
    ) -> None:
        self.session_factory, self.now = session_factory, now
        self.drives, self.offers, self.reviews = drives, offers, reviews

    def ingest(self, entry: PriceInput, request_id: UUID) -> dict[str, Any]:
        """Record, queue or ignore one observation of a described offer. A save key used before
        is answered as it was, and refused for another submission."""
        with self.session_factory() as session:
            replay = self.offers.claim(session, request_id, fingerprint(entry))
            if replay is not None:
                return replay
            result = self._take(session, entry, observation(entry))
            self.offers.answer(session, request_id, result)
            session.commit()
            return result

    def _take(self, session: Session, entry: PriceInput, price: dict[str, Any]) -> dict[str, Any]:
        collected = entry.provenance == "collected"
        listing = (
            None
            if entry.url is None
            else Listing.of(
                str(entry.store), str(entry.url), entry.seller, entry.mpn, entry.condition
            )
        )
        decided = self.reviews.decision_for(session, listing) if collected and listing else None
        said = {
            "mpn": entry.mpn,
            "store": entry.store,
            "seller": entry.seller,
            "condition": entry.condition,
        }
        identity = as_decided(said, decided)
        if identity is None:
            return {"status": "ignored"}
        # Every MPN this may touch, before any row: the drive's, and the others its page gives.
        self.drives.hold(session, [identity["mpn"], *entry.aliases])
        reason = missing_detail(identity["mpn"], identity["condition"])
        # What a person entered is taken as entered; a listing a person decided, as decided while
        # its page reads as it did then. What is collected otherwise is judged as it reads.
        judged = decided is None or entry.title != decided["reviewed_title"]
        # Doubted, it would wait for a person, who is shown its page: one without a page is not.
        if reason is None and collected and judged and listing is not None:
            # Its capacity is what it is recorded under: the page's, or else its drive's (always
            # its drive's once a person has said what it is).
            stated = entry.capacity_gb if decided is None else None
            capacity = stated or self.drives.capacity_of(session, identity["mpn"])
            reason = doubt(entry.title, capacity, identity["mpn"])
            owner = self.drives.owner_of(session, identity["mpn"])
            if reason is not None and owner is not None:
                # What was recorded of the offer this listing is of counts for nothing until a
                # person settles it; other offers of its page are no more in doubt than before.
                self.offers.hold(
                    session, drive_id=owner, store=identity["store"], seller=identity["seller"],
                    condition=identity["condition"], reason=reason,
                )  # fmt: skip
        if reason is not None:
            return self._queue(session, entry, listing, identity, price, reason)
        try:
            # Held apart, so that what it wrote before finding it cannot be taken is undone.
            with session.begin_nested():
                # Once a person has said what a page is, the capacity of its drive stands,
                # whatever the page goes on saying.
                drive_id = self.drives.register(
                    session, identity["mpn"], entry.capacity_gb if decided is None else None
                )
                fresh = self._other_mpns(session, drive_id, entry.aliases)
                offer_id = self.offers.offer_for(
                    session, drive_id=drive_id, store=identity["store"], seller=identity["seller"],
                    condition=identity["condition"], title=entry.title,
                    url=None if listing is None else listing.url,
                )  # fmt: skip
                price_id = self.offers.record(session, offer_id, price, entry.provenance)
                if collected:
                    # Collected afresh and taken as it reads: no longer in doubt.
                    self.offers.release(session, offer_id)
                specifications = entry.specifications
                self.drives.describe(
                    session, drive_id,
                    None if specifications is None else specifications.model_dump(mode="json"),
                    entry.brand,
                )  # fmt: skip
                for alias in fresh:
                    self.drives.attach_alias(session, drive_id, alias)
        except PriceRequired:
            if not collected:
                raise
            # Only a sold-out offer lacks a price, and one never seen in stock has no real price
            # to track yet.
            return {"status": "ignored"}
        except (CapacityConflict, CapacityRequired) as error:
            if entry.on_unmatched != "queue":
                raise
            return self._queue(session, entry, listing, identity, price, queue_reason(error))
        except _NamesAnotherDrive as conflict:
            return self._queue(
                session, entry, listing, identity, price, "alias_conflict",
                conflict_mpn=conflict.mpn, conflict_drive_id=conflict.drive_id,
            )  # fmt: skip
        if collected and listing is not None:
            # This listing no longer waits for review; any other of its page still does.
            self.reviews.clear(session, listing)
        return recorded(offer_id, price_id)

    def _other_mpns(self, session: Session, drive_id: UUID, aliases: list[str]) -> list[str]:
        """The other MPNs a page gives for a drive that no drive goes by yet. One another drive
        goes by refuses the whole observation: no drive is merged for it."""
        fresh = []
        for alias in dict.fromkeys(aliases):
            owner = self.drives.owner_of(session, alias)
            if owner is None:
                fresh.append(alias)
            elif owner != drive_id:
                raise _NamesAnotherDrive(alias, owner)
        return fresh

    def _queue(
        self,
        session: Session,
        entry: PriceInput,
        listing: Listing | None,
        identity: dict[str, Any],
        price: dict[str, Any],
        reason: str,
        **conflict: Any,
    ) -> dict[str, Any]:
        # Only one with its page waits for a reviewer (catalog.schemas.PriceInput asks it of one).
        assert listing is not None
        fields = queued_fields(entry.model_dump(mode="json"), identity, price, reason) | conflict
        item_id = self.reviews.queue(session, listing, fields, entry.observed_at or self.now())
        return {"status": "queued", "review_item_id": str(item_id)}
