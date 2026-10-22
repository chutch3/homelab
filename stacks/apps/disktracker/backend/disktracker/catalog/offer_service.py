"""Offers and their prices as people read and correct them: every offer of a store or a drive, an
offer with its history, a part of the prices of a drive or an offer; and an offer's title or page changed, an offer removed
with its prices, a price recorded by mistake removed (and its offer with it when it was the
offer's last). Each is one piece of work on the offer alone, held against other changes."""

from typing import Any
from uuid import UUID

from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.schemas import OfferEdit, OfferQuery, PriceQuery
from disktracker.database import SessionFactory


class OfferService:
    def __init__(
        self,
        session_factory: SessionFactory,
        snapshot_factory: SessionFactory,
        offers: OfferRepository,
    ) -> None:
        self.session_factory, self.snapshot_factory = session_factory, snapshot_factory
        self.offers = offers

    def listed(self, query: OfferQuery) -> list[dict[str, Any]]:
        with self.snapshot_factory() as session:
            return self.offers.listed(session, query.store, query.drive_id)

    def get(self, offer_id: UUID) -> dict[str, Any]:
        with self.snapshot_factory() as session:
            return self.offers.with_history(session, offer_id)

    def prices(self, query: PriceQuery) -> dict[str, Any]:
        """A part of the prices of a drive's offers or of one offer, with how many there are."""
        with self.snapshot_factory() as session:
            items, total = self.offers.price_page(
                session, query.drive_id, query.offer_id, query.since, query.until,
                query.limit, query.offset,
            )  # fmt: skip
        return {"items": items, "total": total, "limit": query.limit, "offset": query.offset}

    def edit(self, offer_id: UUID, entry: OfferEdit) -> dict[str, Any]:
        """Change what is given of an offer, its page kept as text, and leave the rest."""
        fields = entry.model_dump(exclude_unset=True)
        if "url" in fields:
            fields["url"] = str(fields["url"]) if fields["url"] else None
        with self.session_factory() as session:
            self.offers.lock(session, offer_id)
            self.offers.edit(session, offer_id, fields)
            offer = self.offers.with_history(session, offer_id)
            session.commit()
            return offer

    def delete(self, offer_id: UUID) -> None:
        with self.session_factory() as session:
            self.offers.lock(session, offer_id)
            self.offers.delete(session, offer_id)
            session.commit()

    def delete_price(self, price_id: UUID) -> None:
        """Remove a price, and its offer with it when it was the offer's last. A price that is
        not there is already removed."""
        with self.session_factory() as session:
            offer_id = self.offers.offer_priced(session, price_id)
            if offer_id is None:
                return
            self.offers.lock(session, offer_id)
            if not self.offers.remove_price(session, offer_id, price_id):
                self.offers.delete(session, offer_id)
            session.commit()
