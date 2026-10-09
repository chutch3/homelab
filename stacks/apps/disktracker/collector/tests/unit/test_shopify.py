import json
from pathlib import Path
from typing import Any

import pytest

from collector.models import ScrapedOffer, Store
from collector.sources.shopify import (
    ShopifySettings,
    capacity_from_tags,
    condition_of,
    mpn_from_sku,
    one_listing_per_drive,
    parse_products,
    part_number_skus,
    product_key,
    recheck_offer,
    specifications_from,
)
from tests.builders import CONDITION_RULES, listing

PAGE = json.loads((Path(__file__).parents[1] / "fixtures/serverpartdeals_page1.json").read_text())
BASE = "https://spd.test"
# ServerPartDeals as disktracker seeds it.
STORE = Store("serverpartdeals", BASE, conditions=CONDITION_RULES)
SPD = ShopifySettings.of(
    {
        "collections": ["hard-drives", "solid-state-drives"],
        "free_shipping": True,
    }
)


def test_parse_turns_every_variant_into_an_offer() -> None:
    offers = parse_products(PAGE["products"], STORE, SPD)
    assert offers[0] == ScrapedOffer(
        source="serverpartdeals",
        url="https://spd.test/products/seagate-exos-x20-st18000nm003d-18tb",
        title=PAGE["products"][0]["title"],
        mpn="ST18000NM003D",
        condition="manufacturer_recertified",
        capacity_gb=18000,
        item_price_cents=51900,
        in_stock=True,
        shipping_cents=0,
        specifications={
            "media_type": "hdd",
            "form_factor": "3_5",
            "interface": "sata",
            "intended_use": ["enterprise"],
        },
        brand="Seagate",
    )
    assert [(offer.mpn, offer.in_stock, offer.item_price_cents) for offer in offers[1:]] == [
        ("WUH721818ALE6L4", False, 48900),
        (None, True, 7499),
    ]
    assert (offers[2].url, offers[2].title) == (
        "https://spd.test/products/intel-d3-s4510-960gb?variant=9003",
        "Intel D3-S4510 960GB SATA 2.5in SSD (Bulk)",
    )


def test_long_titles_are_trimmed_to_what_disktracker_accepts() -> None:
    product = {**PAGE["products"][0], "title": "x" * 200}
    [offer] = parse_products([product], STORE, SPD)
    assert offer.title == "x" * 160


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("condition:New", "new"),
        ("condition:Manufacturer Recertified", "manufacturer_recertified"),
        ("condition:Recertified", "refurbished"),
        ("condition:Refurbished", "refurbished"),
        ("condition:Seller Refurbished", "refurbished"),
        ("condition:Used", "used"),
        ("condition:Open Box", "used"),
        ("condition:Mystery", None),
    ],
)
def test_condition_from_tags(tag: str, expected: str | None) -> None:
    product = {"title": "Exos 18TB", "tags": ["brand:X", tag]}
    assert condition_of(product, CONDITION_RULES) == expected


def test_condition_is_unknown_without_a_tag_or_a_title_naming_one() -> None:
    assert condition_of({"title": "Exos 18TB", "tags": ["brand:X"]}, CONDITION_RULES) is None


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("capacity:18TB", 18000),
        ("capacity:1.92TB", 1920),
        ("capacity:960GB", 960),
        ("capacity:128GB", 128),
        ("capacity:big", None),
    ],
)
def test_capacity_from_tags_is_whole_gigabytes(tag: str, expected: int | None) -> None:
    assert capacity_from_tags([tag]) == expected


@pytest.mark.parametrize(
    ("sku", "expected"),
    [
        ("ST18000NM003D_MR", "ST18000NM003D"),
        ("WUH721818ALE6L4", "WUH721818ALE6L4"),
        ("", None),
        (None, None),
    ],
)
def test_mpn_from_sku(sku: str | None, expected: str | None) -> None:
    assert mpn_from_sku(sku) == expected


def product(sku: str, condition: str, price: str, handle: str) -> dict[str, Any]:
    return {
        "handle": handle,
        "tags": [f"condition:{condition}"],
        "variants": [
            {"id": 1, "title": "Default Title", "sku": sku, "price": price, "available": True}
        ],
    }


def test_one_listing_per_drive_prefers_the_bare_drive_then_the_cheapest() -> None:
    g14 = product("0HNHWC_DELLG14_SR", "Refurbished", "499.00", "g14")
    bare = product("0HNHWC_NOTRAY_SR", "Refurbished", "499.00", "bare")
    g13 = product("0HNHWC_DELLG13_SR_7", "Refurbished", "489.00", "g13")
    new_g14 = product("0HNHWC_DELLG14_NB", "New", "879.00", "new-g14")
    new_g13 = product("0HNHWC_DELLG13_NB", "New", "869.00", "new-g13")
    chosen = one_listing_per_drive([g14, bare, g13, new_g14, new_g13], CONDITION_RULES, {"0HNHWC"})
    assert [p["handle"] for p in chosen] == ["bare", "new-g13"]


def test_listings_without_a_sku_are_never_merged() -> None:
    first = product("", "Used", "10.00", "first")
    second = product("", "Used", "20.00", "second")
    assert one_listing_per_drive([first, second], CONDITION_RULES, set()) == [first, second]


def test_parse_names_oem_listings_by_the_maker_mpn_found_in_any_sibling_title() -> None:
    bare = {
        **product("0HNHWC_NOTRAY_SR", "Refurbished", "499.00", "bare"),
        "title": "Dell/Western Digital Ultrastar DC HC550 WUH721816AL5205 16TB",
    }
    new = {**product("0HNHWC_DELLG14_NB", "New", "879.00", "new"), "title": "Dell G14 0HNHWC 16TB"}
    plain = {
        **product("ST18000NM003D_MR", "Refurbished", "519.00", "plain"),
        "title": "Seagate Exos X20 ST18000NM003D 18TB",
    }
    offers = parse_products([bare, new, plain], STORE, SPD)
    assert [(offer.mpn, offer.aliases) for offer in offers] == [
        ("WUH721816AL5205", ("0HNHWC",)),
        ("WUH721816AL5205", ("0HNHWC",)),
        ("ST18000NM003D", ()),
    ]


@pytest.mark.parametrize(
    ("url", "key"),
    [
        (f"{BASE}/products/exos-x18", ("exos-x18", None)),
        (f"{BASE}/collections/hard-drives/products/exos-x18", ("exos-x18", None)),
        ("https://www.spd.test/products/exos-x18", ("exos-x18", None)),
        (f"{BASE}/products/exos-x18?variant=42", ("exos-x18", "42")),
        (f"{BASE}/products/exos-x18/", ("exos-x18", None)),
        ("https://example.com/products/exos-x18", None),
        (f"{BASE}/collections/hard-drives", None),
    ],
)
def test_product_key_names_a_product_page_however_its_url_is_written(
    url: str, key: tuple[str, str | None] | None
) -> None:
    assert product_key(url, BASE) == key


def test_a_sold_out_product_is_reported_at_the_price_the_feed_shows() -> None:
    # disktracker records no price for a sold-out offer, so a placeholder price does no harm.
    product = {**PAGE["products"][1]}
    product["variants"] = [{**product["variants"][0], "price": "10000.00", "available": False}]
    [offer] = parse_products([product], STORE, SPD)
    assert (offer.item_price_cents, offer.in_stock) == (1_000_000, False)


def test_a_gone_page_marks_the_offer_unavailable_without_a_price() -> None:
    assert recheck_offer(listing(f"{BASE}/products/gone"), None, STORE, SPD) == ScrapedOffer(
        source="serverpartdeals",
        url=f"{BASE}/products/gone",
        title="Seagate Exos X18 18TB",
        mpn="ST18000NM000J",
        condition="manufacturer_recertified",
        capacity_gb=18000,
        item_price_cents=None,
        in_stock=False,
        shipping_cents=0,
    )


@pytest.mark.parametrize(
    ("price", "available", "expected"),
    [
        (46800, False, (46800, False)),
        (30000, True, (30000, True)),
    ],
    ids=["sold out", "in stock"],
)
def test_a_page_reports_its_listed_price_and_stock(
    price: int, available: bool, expected: tuple[int | None, bool]
) -> None:
    page = {"variants": [{"id": 7, "price": price, "available": available}]}
    offer = recheck_offer(listing(f"{BASE}/products/x18"), page, STORE, SPD)
    assert (offer.item_price_cents, offer.in_stock) == expected


def test_a_page_with_several_variants_reports_the_one_in_the_offers_url() -> None:
    page = {
        "variants": [
            {"id": 1, "price": 1_000_000, "available": False},
            {"id": 2, "price": 45000, "available": True},
        ]
    }
    offer = recheck_offer(listing(f"{BASE}/products/multi?variant=2"), page, STORE, SPD)
    assert (offer.url, offer.item_price_cents, offer.in_stock) == (
        f"{BASE}/products/multi?variant=2",
        45000,
        True,
    )


@pytest.mark.parametrize(
    ("product_type", "tags", "expected"),
    [
        (
            "Hard Drives > 18TB > 3.5 > SATA > 7.2K",
            ["formFactor:3.5", "interface:SATA"],
            {"media_type": "hdd", "form_factor": "3_5", "interface": "sata"},
        ),
        ("HDDs", ["interface:SAS-4"], {"media_type": "hdd", "interface": "sas"}),
        (
            "Solid State Drives > 3.84TB > 2.5 > NVMe",
            ["formFactor:2.5", "interface:PCIe Gen 4.0 x4"],
            {"media_type": "ssd", "form_factor": "2_5", "interface": "nvme_pcie"},
        ),
        (
            "SSDs",
            ["formFactor:M.2", "interface:NVMe"],
            {"media_type": "ssd", "form_factor": "m_2", "interface": "nvme_pcie"},
        ),
        ("Drive Caddies", ["formFactor:5.25", "interface:Fibre Channel"], None),
        ("", [], None),
    ],
)
def test_specifications_from_a_products_type_and_tags(
    product_type: str, tags: list[str], expected: dict[str, str] | None
) -> None:
    assert specifications_from({"product_type": product_type, "tags": tags}) == expected


def test_recording_and_intended_use_come_from_the_product_title() -> None:
    product = {
        "title": "Seagate IronWolf Pro ST12000NT001 12TB CMR NAS Hard Drive",
        "product_type": "Hard Drives",
        "tags": [],
    }
    assert specifications_from(product) == {
        "media_type": "hdd",
        "recording_type": "cmr",
        "intended_use": ["nas"],
    }


def test_the_brand_tag_names_the_maker_when_the_title_does_not() -> None:
    product = {
        "handle": "exos-18tb",
        "title": "Exos X18 18TB SATA 3.5in Hard Drive",
        "tags": ["brand:Seagate", "capacity:18TB", "condition:Recertified"],
        "variants": [
            {"id": 1, "title": "Default Title", "sku": "X18", "price": "199.00", "available": True}
        ],
    }
    [offer] = parse_products([product], STORE, SPD)
    assert offer.brand == "Seagate"


PLAIN = ShopifySettings.of({"collections": ["drives"], "free_shipping": False})


def test_a_store_whose_skus_are_not_mpns_lists_every_product_and_names_drives_by_title() -> None:
    bare = {
        **product("0HNHWC_NOTRAY_SR", "Refurbished", "499.00", "bare"),
        "title": "Dell/Western Digital Ultrastar DC HC550 WUH721816AL5205 16TB",
    }
    tray = {**product("0HNHWC_DELLG14_SR", "Refurbished", "489.00", "tray"), "title": "Dell 16TB"}
    offers = parse_products([bare, tray], STORE, PLAIN)
    assert [(offer.mpn, offer.aliases) for offer in offers] == [("WUH721816AL5205", ()), (None, ())]


def test_without_free_shipping_shipping_is_unknown() -> None:
    [offer] = parse_products([PAGE["products"][1]], STORE, PLAIN)
    assert offer.shipping_cents is None
    page = {"variants": [{"id": 7, "price": 46800, "available": False}]}
    rechecked = recheck_offer(listing(f"{BASE}/products/x18"), page, STORE, PLAIN)
    assert rechecked.shipping_cents is None


def titled(title: str, sku: str) -> dict[str, Any]:
    return {**product(sku, "New", "100.00", sku.lower()), "title": title}


def test_a_store_whose_titles_name_their_skus_keys_every_sku_by_part_number() -> None:
    feed = [
        titled("Seagate Exos ST18000NM003D 18TB", "ST18000NM003D_MR"),
        titled("WD HC550 WUH721818ALE6L4 18TB", "WUH721818ALE6L4_R"),
        titled("Dell HC320 8TB", "044YFV_NOTRAY_SR"),
    ]
    assert part_number_skus(feed) == {"ST18000NM003D", "WUH721818ALE6L4", "044YFV"}


def test_a_store_with_its_own_sku_codes_keeps_only_those_a_title_names() -> None:
    feed = [
        titled("Seagate Exos 18TB", "SO-1001"),
        titled("WD Red 12TB", "SO-1002"),
        titled("Toshiba MG09ACA18TE 18TB", "MG09ACA18TE"),
    ]
    assert part_number_skus(feed) == {"MG09ACA18TE"}
    assert part_number_skus([]) == set()
