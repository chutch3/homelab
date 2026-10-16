"""Listings shaped exactly as disktracker's API returns them.

Every builder output is parsed by the generated client's model, so a fake that drifts from the
backend's published contract fails here instead of passing silently."""

from typing import Any
from uuid import UUID, uuid4

from listing_text.readers import condition_rules

from collector.models import SourceView
from disktracker_api.models import (
    ManualSourceView,
    OfferSummary,
    SapCommerceSourceView,
    ShopifySourceView,
    SitemapSourceView,
)

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


def offer_json(
    url: str | None,
    *,
    offer_id: UUID | None = None,
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
        "provenance": "collected",
        "total_cents": 36999,
        "price_per_tb": "20.56",
    }
    data: dict[str, Any] = {
        "id": str(offer_id or uuid4()),
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
            # As the API gives a drive back: every specification, unknown where nobody said.
            "specifications": {
                "media_type": "unknown",
                "form_factor": "unknown",
                "interface": "sata",
                "recording_type": "cmr",
                "intended_use": [],
            },
        },
        "latest": observation,
        "doubt": None,
    }
    OfferSummary.from_dict(data)
    return data


def known_offer(url: str | None, **fields: Any) -> OfferSummary:
    return OfferSummary.from_dict(offer_json(url, **fields))


def source_view(
    key: str = "store",
    kind: str = "shopify",
    settings: dict[str, Any] | None = None,
    transport: str = "direct",
) -> SourceView:
    """A source as disktracker says it is due, with every setting of its kind: blank unless
    given."""
    view, blank = VIEWS[kind]
    return view.from_dict(
        {
            "id": str(UUID(int=len(key))),
            "key": key,
            "name": key,
            "kind": kind,
            "base_url": "https://store.test/",
            "settings": {**blank(), **(settings or {})},
            "schedule": "0 3 * * *",
            "enabled": True,
            "transport": transport,
            "basis": "unconfirmed",
            "obey_robots": True,
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


def sap_commerce_settings(**given: str) -> dict[str, str]:
    """An SAP Commerce source's settings as disktracker gives them: blank unless given."""
    names = ("api_url", "site", "sitemap_path", "product_path_pattern", "recertified_sku_prefix")
    return {**dict.fromkeys(names, ""), **given}


# Each kind's source, and its settings with nothing set.
VIEWS: dict[str, tuple[type[SourceView], Any]] = {
    "manual": (ManualSourceView, dict),
    "shopify": (ShopifySourceView, lambda: {"collections": [], "free_shipping": False}),
    "sitemap": (SitemapSourceView, sitemap_settings),
    "sap_commerce": (SapCommerceSourceView, sap_commerce_settings),
}
