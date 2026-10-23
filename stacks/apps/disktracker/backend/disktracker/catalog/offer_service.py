"""Offers and their prices as people read and correct them: every offer of a store or a drive, an
offer with its history, a part of the prices of a drive or an offer; and an offer's title or page changed, an offer removed
with its prices, a price recorded by mistake removed (and its offer with it when it was the
offer's last). Each is one piece of work on the offer alone, held against other changes."""

from typing import Any
from uuid import UUID

from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.schemas import OfferEdit, OfferQuery, PriceQuery
from disktracker.database import Transactions, transactional


class OfferService:
    def __init__(
        self,
        transactions: Transactions,
        offers: OfferRepository,
    ) -> None:
        self.transactions = transactions
        self.offers = offers

    @transactional(read_only=True)
    def listed(self, query: OfferQuery) -> list[dict[str, Any]]:
        return self.offers.listed(query.store, query.drive_id)

    @transactional(read_only=True)
    def get(self, offer_id: UUID) -> dict[str, Any]:
        return self.offers.with_history(offer_id)

    @transactional(read_only=True)
    def prices(self, query: PriceQuery) -> dict[str, Any]:
        """A part of the prices of a drive's offers or of one offer, with how many there are."""
        items, total = self.offers.price_page(
            query.drive_id, query.offer_id, query.since, query.until,
            query.limit, query.offset,
        )  # fmt: skip
        return {"items": items, "total": total, "limit": query.limit, "offset": query.offset}

    @transactional
    def edit(self, offer_id: UUID, entry: OfferEdit) -> dict[str, Any]:
        """Change what is given of an offer, its page kept as text, and leave the rest."""
        fields = entry.model_dump(exclude_unset=True)
        if "url" in fields:
            fields["url"] = str(fields["url"]) if fields["url"] else None
        self.offers.lock(offer_id)
        self.offers.edit(offer_id, fields)
        return self.offers.with_history(offer_id)

    @transactional
    def delete(self, offer_id: UUID) -> None:
        self.offers.lock(offer_id)
        self.offers.delete(offer_id)

    @transactional
    def delete_price(self, price_id: UUID) -> None:
        """Remove a price, and its offer with it when it was the offer's last. A price that is
        not there is already removed."""
        offer_id = self.offers.offer_priced(price_id)
        if offer_id is None:
            return
        self.offers.lock(offer_id)
        if not self.offers.remove_price(offer_id, price_id):
            self.offers.delete(offer_id)
