"""Deciding what a listing waiting for review is: nothing to track, or a drive already recorded
in a condition. As one piece of work: the decision and its answer, the item leaving the queue,
what is recorded of it through the one price writer, the drive given what the page said of it
where nobody has, the offer no longer held, and the decision remembered for later prices of
that listing. The same decision sent again gets the first answer and changes nothing; a
different one is refused."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.review_repository import ReviewRepository, listing_of
from disktracker.catalog.schemas import MatchDecision, ObservationInput
from disktracker.catalog.schemas import ReviewDecision as Decision
from disktracker.database import SessionFactory
from disktracker.errors import DriveNotFound


class ReviewService:
    def __init__(
        self,
        session_factory: SessionFactory,
        drives: DriveRepository,
        offers: OfferRepository,
        reviews: ReviewRepository,
    ) -> None:
        self.session_factory = session_factory
        self.drives, self.offers, self.reviews = drives, offers, reviews

    def decide(self, item_id: UUID, decision: Decision) -> dict[str, Any]:
        with self.session_factory() as session:
            replay = self.reviews.claim_decision(session, item_id, decision.model_dump(mode="json"))
            if replay is not None:
                return replay
            drive = None
            if isinstance(decision, MatchDecision):
                # Every MPN this may touch, then the drive, before the item: what the drive goes
                # by, and the others its page gave (the catalog-wide lock order).
                aliases = self.reviews.peek(session, item_id)["aliases"] or []
                goes_by = self.drives.identifiers(session, decision.drive_id)
                self.drives.hold(session, [*goes_by, *aliases])
                # Merged away while its MPNs were awaited, it is gone.
                drive = self.drives.lock_drives(session, [decision.drive_id]).get(decision.drive_id)
                if drive is None:
                    raise DriveNotFound()
            item = self.reviews.take(session, item_id)
            if isinstance(decision, MatchDecision):
                assert drive is not None
                result = self._match(session, item, decision, drive["mpn"])
            else:
                self.reviews.remember(
                    session, listing_of(item), mpn=None, condition=None, ignored=True,
                    reviewed_title=item["title"],
                )  # fmt: skip
                result = {"status": "ignored", "offer_id": None}
            self.reviews.answer_decision(session, item_id, result)
            session.commit()
            return result

    def _match(
        self, session: Session, item: dict[str, Any], decision: MatchDecision, mpn: str
    ) -> dict[str, Any]:
        drive_id = decision.drive_id
        price = ObservationInput.model_validate(
            {key: item[key] for key in ("item_price_cents", "shipping_cents", "in_stock")}
            | {"observed_at": item["last_seen_at"]}
        )
        offer_id = self.offers.offer_for(
            session, drive_id=drive_id, store=item["store"], seller=item["seller"],
            condition=decision.condition, title=item["title"], url=item["url"],
        )  # fmt: skip
        self.offers.record(session, offer_id, price.model_dump(), item["provenance"])
        # A person has said what it is: it is no longer in doubt.
        self.offers.release(session, offer_id)
        # What the page said of the drive, where nobody has said it. Another MPN it gave that
        # another drive goes by stays that drive's: nothing is merged.
        self.drives.describe(session, drive_id, item["specifications"], item["brand"])
        for alias in dict.fromkeys(item["aliases"] or []):
            if self.drives.owner_of(session, alias) is None:
                self.drives.attach_alias(session, drive_id, alias)
        self.reviews.remember(
            session, listing_of(item), mpn=mpn, condition=decision.condition,
            ignored=False, reviewed_title=item["title"],
        )  # fmt: skip
        return {"status": "matched", "offer_id": str(offer_id)}
