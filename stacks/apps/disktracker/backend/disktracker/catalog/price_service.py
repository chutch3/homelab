"""Recording a price for an offer whose drive is already known, named by its id or by its drive,
store, seller and condition: claim its save key, find or make the offer, keep the price or count
it as a check through the one price writer (catalog.offer_repository), and keep the answer, as
one piece of work. Nothing is decided of the drive, and the offer stays held or not as it
was."""

from hashlib import sha256
from typing import Any
from uuid import UUID

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.schemas import ObservationInput, PriceInput
from disktracker.database import Transactions, transactional
from disktracker.errors import DriveNotFound


def observation(entry: ObservationInput, collected: bool) -> dict[str, Any]:
    """The price a submission observed. Sold out is only a stock state for a collected one:
    whatever price the store shows then (a placeholder, say) is not recorded, so the offer keeps
    the price it last had in stock."""
    price = entry.model_dump(include=set(ObservationInput.model_fields))
    if collected and not entry.in_stock:
        price |= {"item_price_cents": None, "shipping_cents": None}
    return price


def fingerprint(kind: str, entry: ObservationInput) -> str:
    """What binds a save key to the submission sent under it, and to what kind it is."""
    return sha256(f"{kind}:{entry.model_dump_json()}".encode()).hexdigest()


def recorded(offer_id: UUID, price_id: UUID | None) -> dict[str, Any]:
    return {
        "status": "recorded",
        "offer_id": str(offer_id),
        "price_id": str(price_id) if price_id else None,
    }


class PriceService:
    def __init__(
        self, transactions: Transactions, drives: DriveRepository, offers: OfferRepository
    ) -> None:
        self.transactions, self.drives, self.offers = transactions, drives, offers

    @transactional
    def record(self, entry: PriceInput, request_id: UUID) -> dict[str, Any]:
        """A price for the offer named, or of the drive named at that store, from that seller,
        in that condition. A save key used before is answered as it was, and refused for another
        submission. It touches no MPN: the drive, then its offer, are held (the catalog-wide lock
        order)."""
        replay = self.offers.claim(request_id, fingerprint("price", entry))
        if replay is not None:
            return replay
        if entry.offer_id is not None:
            offer_id = entry.offer_id
            self.offers.lock(offer_id)
        else:
            # Validated: an offer not named is placed (catalog.schemas.PriceInput).
            assert entry.drive_id and entry.store and entry.condition
            if not self.drives.lock_drives([entry.drive_id]):
                raise DriveNotFound()
            offer_id = self.offers.offer_for(
                drive_id=entry.drive_id, store=entry.store, seller=entry.seller,
                condition=entry.condition, title=entry.title,
                url=None if entry.url is None else str(entry.url),
            )  # fmt: skip
        collected = entry.provenance == "collected"
        price = observation(entry, collected)
        price_id = self.offers.record(offer_id, price, entry.provenance)
        result = recorded(offer_id, price_id)
        self.offers.answer(request_id, result)
        return result
