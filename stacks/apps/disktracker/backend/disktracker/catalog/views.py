"""The catalog as the API shows it: drives, prices, offers and review items, made from the rows
they are kept in. Pure: rows in, response data out."""

from datetime import UTC, datetime
from typing import Any

from disktracker.catalog.models import Drive, Offer, Price, ReviewItem
from disktracker.catalog.rules import comparable_price
from disktracker.catalog.schemas import Specifications
from disktracker.database import columns


def timestamp(value: datetime) -> str:
    """How a moment is written in what the API returns."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def drive_view(drive: Drive, aliases: list[str]) -> dict[str, Any]:
    return {
        "id": str(drive.id),
        "mpn": drive.mpn,
        "aliases": aliases,
        "brand": drive.brand,
        "capacity_gb": drive.capacity_gb,
        "specifications": Specifications.model_validate(drive.specifications).model_dump(
            mode="json"
        ),
    }


def price_view(price: Price, capacity_gb: int) -> dict[str, Any]:
    total, unit = comparable_price(price.item_price_cents, price.shipping_cents, capacity_gb)
    return {
        "id": str(price.id),
        "item_price_cents": price.item_price_cents,
        "shipping_cents": price.shipping_cents,
        "shipping_known": price.shipping_cents is not None,
        "in_stock": price.in_stock,
        "observed_at": timestamp(price.observed_at),
        "entered_at": timestamp(price.entered_at),
        "notes": price.notes,
        "provenance": price.provenance,
        "total_cents": total,
        "price_per_tb": unit,
    }


def summary_view(
    offer: Offer,
    drive: Drive,
    aliases: list[str],
    latest: Price,
    store_name: str,
    doubt: str | None,
) -> dict[str, Any]:
    """An offer with its latest price, and why it is doubted, if it is. It was checked when it
    was last priced, or later."""
    checked = max(latest.observed_at, offer.last_checked_at or latest.observed_at)
    return {
        "id": str(offer.id),
        "title": offer.title,
        "mpn": offer.mpn,
        "store": offer.store,
        "store_name": store_name,
        "seller": offer.seller,
        "url": offer.url,
        "condition": offer.condition,
        "last_checked_at": timestamp(checked),
        "drive": drive_view(drive, aliases),
        "capacity_gb": drive.capacity_gb,
        "latest": price_view(latest, drive.capacity_gb),
        "doubt": doubt,
    }


def review_item_view(item: ReviewItem, drive: dict[str, Any] | None) -> dict[str, Any]:
    return {
        **columns(item),
        "drive": drive,
        "id": str(item.id),
        "first_seen_at": timestamp(item.first_seen_at),
        "last_seen_at": timestamp(item.last_seen_at),
    }
