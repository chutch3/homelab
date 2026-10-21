"""Offers and prices as people correct them: an offer's title or page changed, an offer removed
with its prices, a price recorded by mistake removed (and its offer with it when it was the
offer's last). Each is one piece of work on the offer alone, held against other changes."""

from typing import Any
from uuid import UUID

from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.queries import offer_with_history
from disktracker.catalog.schemas import OfferEdit
from disktracker.database import SessionFactory


class OfferService:
    def __init__(self, session_factory: SessionFactory, offers: OfferRepository) -> None:
        self.session_factory, self.offers = session_factory, offers

    def edit(self, offer_id: UUID, entry: OfferEdit) -> dict[str, Any]:
        """Change what is given of an offer, its page kept as text, and leave the rest."""
        fields = entry.model_dump(exclude_unset=True)
        if "url" in fields:
            fields["url"] = str(fields["url"]) if fields["url"] else None
        with self.session_factory() as session:
            self.offers.lock(session, offer_id)
            self.offers.edit(session, offer_id, fields)
            offer = offer_with_history(session, offer_id)
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
