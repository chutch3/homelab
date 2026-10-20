"""Recording a price for an offer already named: claim its save key, keep the price or count it as
a check through the one price writer (catalog.offer_repository), and keep the answer, as one
piece of work. Nothing else is decided of the offer: it stays held or not as it was."""

from hashlib import sha256
from typing import Any
from uuid import UUID

from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.schemas import ObservationInput, PriceInput
from disktracker.database import SessionFactory


def observation(entry: PriceInput) -> dict[str, Any]:
    """The price a submission observed. Sold out is only a stock state for a collected one:
    whatever price the store shows then (a placeholder, say) is not recorded, so the offer keeps
    the price it last had in stock."""
    price = entry.model_dump(include=set(ObservationInput.model_fields))
    if entry.provenance == "collected" and not entry.in_stock:
        price |= {"item_price_cents": None, "shipping_cents": None}
    return price


def fingerprint(entry: PriceInput) -> str:
    """What binds a save key to the submission sent under it."""
    return sha256(f"price:{entry.model_dump_json()}".encode()).hexdigest()


def recorded(offer_id: UUID, price_id: UUID | None) -> dict[str, Any]:
    return {
        "status": "recorded",
        "offer_id": str(offer_id),
        "price_id": str(price_id) if price_id else None,
    }


class PriceService:
    def __init__(self, session_factory: SessionFactory, offers: OfferRepository) -> None:
        self.session_factory, self.offers = session_factory, offers

    def record(self, offer_id: UUID, entry: PriceInput, request_id: UUID) -> dict[str, Any]:
        """A price for the offer named. A save key used before is answered as it was, and
        refused for another submission."""
        with self.session_factory() as session:
            replay = self.offers.claim(session, request_id, fingerprint(entry))
            if replay is not None:
                return replay
            self.offers.lock(session, offer_id)
            price_id = self.offers.record(session, offer_id, observation(entry), entry.provenance)
            result = recorded(offer_id, price_id)
            self.offers.answer(session, request_id, result)
            session.commit()
            return result
