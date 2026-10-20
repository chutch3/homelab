"""Deciding what a listing waiting for review is: nothing to track, or a drive in a condition. As
one piece of work: the decision and its answer, the item leaving the queue, what is recorded of
it through the one price writer, the drive corrected when the reviewer says so and given what the
page said of it where nobody has, the offer no longer held, and the decision remembered for later
prices of that listing. The same decision sent again gets the first answer and changes nothing; a
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
            if isinstance(decision, MatchDecision):
                # Every MPN this may touch, before the item: the drive's, and the others its
                # page gave (the catalog-wide lock order).
                aliases = self.reviews.peek(session, item_id)["aliases"] or []
                self.drives.hold(session, [decision.mpn, *aliases])
            item = self.reviews.take(session, item_id)
            if isinstance(decision, MatchDecision):
                result = self._match(session, item, decision)
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
        self, session: Session, item: dict[str, Any], decision: MatchDecision
    ) -> dict[str, Any]:
        known = self.drives.capacity_of(session, decision.mpn)
        if decision.correct_drive and known is not None and decision.capacity_gb is not None:
            self.drives.correct_capacity(session, decision.mpn, decision.capacity_gb)
        # Left unsaid, a drive already recorded keeps its capacity, whatever the page said; a new
        # one takes the page's.
        capacity = decision.capacity_gb
        if capacity is None and known is None:
            capacity = item["capacity_gb"]
        drive_id = self.drives.register(session, decision.mpn, capacity)
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
            session, listing_of(item), mpn=decision.mpn, condition=decision.condition,
            ignored=False, reviewed_title=item["title"],
        )  # fmt: skip
        return {"status": "matched", "offer_id": str(offer_id)}
