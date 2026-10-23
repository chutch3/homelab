"""Taking in one observation of a store page as collected, its offer described rather than
named: what its listing has been decided to be, what disktracker knows of its drive, and what
that makes of it (catalog.verdict): the drive it is of registered when new, the price recorded
through the one price writer and what its page says of the drive kept; or it waits for review,
or is ignored. One piece of work with its save key: all of it is kept, or none. What would become
of a page is foreseen the same way, keeping nothing."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.price_service import fingerprint, observation, recorded
from disktracker.catalog.review_repository import Listing, ReviewRepository
from disktracker.catalog.rules import as_decided, normalize_mpn, queued_fields
from disktracker.catalog.schemas import IngestionInput
from disktracker.catalog.verdict import Known, Seen, Verdict, judged
from disktracker.clock import Clock
from disktracker.database import SessionFactory


class CollectedPage(BaseModel):
    """What a page as the collector read it says, apart from its store and price."""

    model_config = ConfigDict(frozen=True)
    url: str
    seller: str = ""
    mpn: str | None = None
    condition: str | None = None
    title: str
    capacity_gb: int | None = None
    aliases: list[str] = []
    in_stock: bool

    @field_validator("seller", mode="before")
    @classmethod
    def no_seller_is_blank(cls, seller: str | None) -> str:
        return seller or ""


class IngestionService:
    def __init__(
        self,
        session_factory: SessionFactory,
        snapshot_factory: SessionFactory,
        drives: DriveRepository,
        offers: OfferRepository,
        reviews: ReviewRepository,
        clock: Clock,
    ) -> None:
        self.session_factory, self.snapshot_factory = session_factory, snapshot_factory
        self.clock = clock
        self.drives, self.offers, self.reviews = drives, offers, reviews

    def ingest(self, entry: IngestionInput, request_id: UUID) -> dict[str, Any]:
        """Record, queue or ignore one observation of a store page as collected. A save key used
        before is answered as it was, and refused for another submission."""
        with self.session_factory() as session:
            replay = self.offers.claim(session, request_id, fingerprint("ingestion", entry))
            if replay is not None:
                return replay
            result = self._take(session, entry, observation(entry, collected=True))
            self.offers.answer(session, request_id, result)
            session.commit()
            return result

    def foresee(self, store: str, page: CollectedPage) -> Verdict:
        """What taking in a page as collected would make of it now, as ingest would; nothing is
        kept."""
        mpn = normalize_mpn(page.mpn) if page.mpn else None
        aliases = [normalize_mpn(alias) for alias in page.aliases]
        listing = Listing.of(store, page.url, page.seller, mpn, page.condition)
        seen = Seen(page.title, page.capacity_gb, tuple(aliases), page.in_stock)
        with self.snapshot_factory() as session:
            decided = self.reviews.decision_for(session, listing)
            identity = as_decided(_said(listing), decided)
            known = self._known(session, identity, aliases, hold=False)
            return judged(seen, identity, decided, known)

    def _known(
        self,
        session: Session,
        identity: dict[str, Any] | None,
        aliases: list[str],
        *,
        hold: bool,
    ) -> Known:
        """What disktracker knows of the drive a page's offer is identified as: what the
        judgement of it reads (catalog.verdict.Known). Held, the drive is held against other
        changes before anything of it is read, so what is judged is what is written to."""
        mpn = None if identity is None else identity["mpn"]
        drive = None if mpn is None else self.drives.owner_of(session, mpn)
        if hold and drive is not None:
            self.drives.lock_drives(session, [drive])
        owners = {
            alias: owner
            for alias in dict.fromkeys(aliases)
            if (owner := self.drives.owner_of(session, alias)) is not None
        }
        priced = identity is not None and drive is not None and self.offers.priced(
            session, drive_id=drive, store=identity["store"], seller=identity["seller"],
            condition=identity["condition"],
        )  # fmt: skip
        capacity = None if mpn is None else self.drives.capacity_of(session, mpn)
        return Known(drive, capacity, owners, priced)

    def _take(
        self, session: Session, entry: IngestionInput, price: dict[str, Any]
    ) -> dict[str, Any]:
        listing = Listing.of(entry.store, str(entry.url), entry.seller, entry.mpn, entry.condition)
        decided = self.reviews.decision_for(session, listing)
        identity = as_decided(_said(listing), decided)
        if identity is None:
            return {"status": "ignored"}
        # Every MPN this may touch, before any row: the drive's, and the others its page gives.
        self.drives.hold(session, [identity["mpn"], *entry.aliases])
        known = self._known(session, identity, entry.aliases, hold=True)
        seen = Seen(entry.title, entry.capacity_gb, tuple(entry.aliases), entry.in_stock)
        verdict = judged(seen, identity, decided, known)
        if verdict.outcome == "ignored":
            return {"status": "ignored"}
        if verdict.outcome == "queued":
            assert verdict.reason is not None
            if verdict.hold:
                # What was recorded of the offer this listing is of counts for nothing until a
                # person settles it; other offers of its page are no more in doubt than before.
                assert known.drive is not None
                self.offers.hold(
                    session, drive_id=known.drive, store=identity["store"],
                    seller=identity["seller"], condition=identity["condition"],
                    reason=verdict.reason,
                )  # fmt: skip
            conflict = (
                {}
                if verdict.conflict is None
                else {"conflict_mpn": verdict.conflict[0], "conflict_drive_id": verdict.conflict[1]}
            )
            return self._queue(session, entry, listing, identity, price, verdict.reason, conflict)
        drive_id = self.drives.register(session, identity["mpn"], verdict.capacity)
        offer_id = self.offers.offer_for(
            session, drive_id=drive_id, store=identity["store"], seller=identity["seller"],
            condition=identity["condition"], title=entry.title, url=listing.url,
        )  # fmt: skip
        price_id = self.offers.record(session, offer_id, price, "collected")
        # Collected afresh and taken as it reads: no longer in doubt.
        self.offers.release(session, offer_id)
        specifications = entry.specifications
        self.drives.describe(
            session, drive_id,
            None if specifications is None else specifications.model_dump(mode="json"),
            entry.brand,
        )  # fmt: skip
        for alias in verdict.fresh:
            self.drives.attach_alias(session, drive_id, alias)
        # This listing no longer waits for review; any other of its page still does.
        self.reviews.clear(session, listing)
        return recorded(offer_id, price_id)

    def _queue(
        self,
        session: Session,
        entry: IngestionInput,
        listing: Listing,
        identity: dict[str, Any],
        price: dict[str, Any],
        reason: str,
        conflict: dict[str, Any],
    ) -> dict[str, Any]:
        submitted = entry.model_dump(mode="json") | {"provenance": "collected"}
        fields = queued_fields(submitted, identity, price, reason) | conflict
        item_id = self.reviews.queue(session, listing, fields, entry.observed_at or self.clock.now())
        return {"status": "queued", "review_item_id": str(item_id)}


def _said(listing: Listing) -> dict[str, Any]:
    """What a page says identifies its offer: None for an MPN or condition it does not give."""
    return {
        "mpn": listing.mpn or None,
        "store": listing.store,
        "seller": listing.seller,
        "condition": listing.condition or None,
    }
