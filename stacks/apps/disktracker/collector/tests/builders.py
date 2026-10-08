"""Listings shaped exactly as disktracker's API returns them.

Every builder output is parsed by the generated client's model, so a fake that drifts from the
backend's published contract fails here instead of passing silently."""

from typing import Any
from uuid import UUID, uuid4

from listing_text.readers import condition_rules

from disktracker_api.models import ListingSummary, SourceView

# The condition rules disktracker is seeded with.
CONDITION_RULES = condition_rules(
    [
        (r"\bmanufacturer recertified\b", "manufacturer_recertified"),
        (r"\bseller refurbished\b", "refurbished"),
        (r"\bopen box\b", "used"),
        (r"\brecertified\b", "refurbished"),
        (r"\brefurbished\b", "refurbished"),
        (r"\brenewed\b", "refurbished"),
        (r"\bused\b", "used"),
        (r"\bnew\b", "new"),
    ]
)

# The stores the backend seeds, by slug.
STORE_NAMES = {
    "serverpartdeals": "ServerPartDeals",
    "goharddrive": "GoHardDrive",
    "westerndigital": "Western Digital",
    "other": "Other",
}


def listing_json(
    url: str | None,
    *,
    listing_id: UUID | None = None,
    store: str = "serverpartdeals",
    seller: str = "",
    title: str = "Seagate Exos X18 18TB",
    mpn: str = "ST18000NM000J",
    condition: str = "manufacturer_recertified",
    capacity_gb: int = 18000,
    in_stock: bool = True,
) -> dict[str, Any]:
    observation = {
        "id": str(uuid4()),
        "item_price_cents": 36999,
        "shipping_cents": 0,
        "shipping_known": True,
        "in_stock": in_stock,
        "observed_at": "2026-09-25T12:00:00Z",
        "entered_at": "2026-09-25T12:00:00Z",
        "notes": "",
        "acquisition_method": "serverpartdeals",
        "total_cents": 36999,
        "price_per_tb": "20.56",
    }
    data: dict[str, Any] = {
        "id": str(listing_id or uuid4()),
        "title": title,
        "mpn": mpn,
        "store": store,
        "store_name": STORE_NAMES.get(store, store),
        "seller": seller,
        "url": url,
        "condition": condition,
        "last_checked_at": "2026-09-25T12:00:00Z",
        "capacity_gb": capacity_gb,
        "drive": {
            "id": str(uuid4()),
            "mpn": mpn,
            "aliases": [],
            "brand": None,
            "capacity_gb": capacity_gb,
            "specifications": {"interface": "sata", "recording_type": "cmr", "intended_use": []},
        },
        "latest": observation,
    }
    ListingSummary.from_dict(data)
    return data


def listing(url: str | None, **fields: Any) -> ListingSummary:
    return ListingSummary.from_dict(listing_json(url, **fields))


def source_view(
    key: str = "store",
    kind: str = "shopify",
    settings: dict[str, Any] | None = None,
    transport: str = "direct",
) -> SourceView:
    """A source as disktracker says it is due."""
    return SourceView.from_dict(
        {
            "id": str(UUID(int=len(key))),
            "key": key,
            "name": key,
            "kind": kind,
            "base_url": "https://store.test/",
            "settings": settings or {},
            "schedule": "0 3 * * *",
            "enabled": True,
            "transport": transport,
            "basis": "unconfirmed",
            "notes": "",
            "next_run_at": None,
        }
    )


def sitemap_settings(**given: str) -> dict[str, str]:
    """A sitemap source's settings as disktracker gives them: every one, blank unless given."""
    names = (
        "sitemap_path",
        "product_path_pattern",
        "free_shipping_marker",
        "data_pattern",
        "data_items",
        "data_model_field",
        "data_name_field",
        "data_price_field",
        "data_brand_field",
        "data_stock_field",
        "data_in_stock_value",
    )
    return {**dict.fromkeys(names, ""), **given}
