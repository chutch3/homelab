"""What drives cost today, by the terabyte: one mark for each drive in each condition some store
has it in stock in, placed at the lowest item price asked for it. Pure."""

from datetime import datetime, timedelta
from typing import Any


def marks(offers: list[dict[str, Any]], now: datetime, recent_days: int) -> list[dict[str, Any]]:
    """offers: each offer's drive, condition, title, capacity, latest item price, whether it is
    in stock, and when it was last checked. Shipping is left out, as it is from every chart. The
    cheapest mark of an offer checked within recent_days is the lowest; one unchecked for longer
    is placed but cannot be lowest. Offers held for a person to settle are not among them."""

    def per_tb(offer: dict[str, Any]) -> float:
        return float(offer["item_price_cents"] * 1000 / offer["capacity_gb"])

    cheapest: dict[tuple[str, str], dict[str, Any]] = {}
    for offer in sorted(
        (offer for offer in offers if offer["in_stock"]), key=lambda o: str(o["id"])
    ):
        key = (str(offer["drive_id"]), offer["condition"])
        if key not in cheapest or per_tb(offer) < per_tb(cheapest[key]):
            cheapest[key] = offer
    placed = sorted(cheapest.values(), key=lambda offer: (per_tb(offer), str(offer["id"])))
    recent = timedelta(days=recent_days)
    lowest = next(
        (offer for offer in placed if timedelta(0) <= now - offer["last_checked_at"] <= recent),
        None,
    )
    return [
        {
            "drive_id": str(offer["drive_id"]),
            "condition": offer["condition"],
            "title": offer["title"],
            "capacity_gb": offer["capacity_gb"],
            "per_tb_cents": round(per_tb(offer)),
            "lowest": offer is lowest,
        }
        for offer in placed
    ]
