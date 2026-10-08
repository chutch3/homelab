import json
from pathlib import Path
from typing import Any

import pytest

from collector.models import Store
from collector.sources.sap_commerce import (
    SapCommerceSettings,
    offer_from_product,
    product_pages,
    recheck_offer,
    sku_of,
)
from tests.builders import CONDITION_RULES, listing

FIXTURES = Path(__file__).parents[1] / "fixtures/westerndigital"
BASE = "https://wd.test"
PAGE = f"{BASE}/products/internal-drives/wd-red-plus-sata-3-5-hdd?sku=WD120EFBX"
RECERTIFIED = f"{BASE}/products/recertified/internal-drives/x-recertified?sku=R0F29590"
# Western Digital as disktracker seeds it.
STORE = Store("westerndigital", BASE, conditions=CONDITION_RULES)
WD = SapCommerceSettings.of(
    {
        "api_url": "https://api.wd.test/wdwebservices/v2",
        "site": "us",
        "sitemap_path": "/products-sitemap.xml",
        "product_path_pattern": "^/products/(recertified/)?internal-drives/",
        "recertified_sku_prefix": "R",
    }
)


def product(sku: str, **changes: Any) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((FIXTURES / f"{sku}.json").read_text())
    return {**loaded, **changes}


def test_the_sitemap_yields_the_pages_to_read_new_ones_first() -> None:
    urls = [
        f"{BASE}{path}"
        for path in [
            "/products/recertified/internal-drives/wd-red-sata-hdd-recertified?sku=RWD40EFAX",
            "/products/external-drives/my-book-usb-3-0-hdd?sku=WDBBGB0040HBK-NESN",
            "/products/internal-drives/wd-gold-sata-hdd?sku=WD2005FBYZ",
            "/products/recertified/external-drives/my-book-hdd-recertified?sku=RWDBBGB0040HBK",
            "/products/internal-drives/data-center-drives/ultrastar-dc-hc550-hdd?sku=0F38352",
        ]
    ]
    assert product_pages(urls, WD) == [
        f"{BASE}/products/internal-drives/wd-gold-sata-hdd?sku=WD2005FBYZ",
        f"{BASE}/products/internal-drives/data-center-drives/ultrastar-dc-hc550-hdd?sku=0F38352",
        f"{BASE}/products/recertified/internal-drives/wd-red-sata-hdd-recertified?sku=RWD40EFAX",
    ]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (PAGE, "WD120EFBX"),
        ("https://WD.test/products/recertified/internal-drives/x?sku=R0F29590", "R0F29590"),
        (f"{BASE}/products/internal-drives/wd-red-plus-sata-3-5-hdd", None),
        ("https://elsewhere.test/products/internal-drives/x?sku=WD120EFBX", None),
    ],
)
def test_a_product_page_names_its_sku(url: str, expected: str | None) -> None:
    assert sku_of(url, BASE) == expected


def test_a_retail_drive_is_known_by_its_model_number() -> None:
    offer = offer_from_product(product("WD120EFBX"), PAGE, STORE, WD)
    assert offer is not None
    assert (offer.mpn, offer.aliases, offer.condition, offer.capacity_gb) == (
        "WD120EFBX",
        (),
        "new",
        12000,
    )
    assert (offer.item_price_cents, offer.in_stock, offer.shipping_cents) == (56499, False, None)


def test_a_data_center_drive_is_known_by_its_model_number_with_the_part_number_as_an_alias() -> (
    None
):
    offer = offer_from_product(product("0F38352"), PAGE, STORE, WD)
    assert offer is not None
    assert (offer.mpn, offer.aliases) == ("WUH721818AL5201", ("0F38352",))
    assert offer.specifications == {
        "media_type": "hdd",
        "interface": "sas",
        "intended_use": ["enterprise"],
    }


def test_a_recertified_drive_is_known_by_its_part_number_without_the_recertified_prefix() -> None:
    offer = offer_from_product(product("R0F29590"), RECERTIFIED, STORE, WD)
    assert offer is not None
    assert (offer.mpn, offer.aliases, offer.condition) == (
        "0F29590",
        (),
        "manufacturer_recertified",
    )


def test_a_recertified_retail_drive_keeps_its_model_number() -> None:
    recertified = product(
        "R0F29590",
        code="RWD40EFAX",
        name="WD Red™ - 4TB",
        classifications=[
            {"code": "cc_shipping", "features": [
                {"codeShort": "modelNumber", "featureValues": [{"value": "RWD40EFAX"}]}
            ]}
        ],
    )  # fmt: skip
    offer = offer_from_product(recertified, RECERTIFIED, STORE, WD)
    assert offer is not None
    assert (offer.mpn, offer.capacity_gb) == ("WD40EFAX", 12000)


def test_capacity_falls_back_to_the_name_and_a_drive_without_one_is_skipped() -> None:
    offer = offer_from_product(product("WD120EFBX", categories=[]), PAGE, STORE, WD)
    assert offer is not None and offer.capacity_gb == 12000
    assert (
        offer_from_product(
            product("WD120EFBX", categories=[], name="WD Red™ Plus"), PAGE, STORE, WD
        )
        is None
    )


def test_a_product_without_a_price_is_not_on_sale() -> None:
    assert offer_from_product(product("ULTRASTAR-DC-HC650-20-TB"), PAGE, STORE, WD) is None


def test_low_stock_is_still_in_stock() -> None:
    low = product("WD120EFBX", stock={"stockLevel": 2, "stockLevelStatus": "lowStock"})
    offer = offer_from_product(low, PAGE, STORE, WD)
    assert offer is not None and offer.in_stock


def test_a_recheck_reposts_the_known_offer_with_what_the_api_says_now() -> None:
    known = listing(PAGE, mpn="WD120EFBX", condition="new", store="westerndigital")
    now = recheck_offer(known, product("WD120EFBX"), STORE)
    assert (now.mpn, now.item_price_cents, now.in_stock, now.source) == (
        "WD120EFBX",
        56499,
        False,
        "westerndigital",
    )
    gone = recheck_offer(known, None, STORE)
    assert (gone.item_price_cents, gone.in_stock) == (None, False)
    unpriced = recheck_offer(
        known, product("WD120EFBX", price=None, stock={"stockLevelStatus": "inStock"}), STORE
    )
    assert (unpriced.item_price_cents, unpriced.in_stock) == (None, False)


def test_a_page_whose_path_says_recertified_is_recertified_and_without_a_prefix_keeps_its_sku() -> (
    None
):
    plain = SapCommerceSettings.of(
        {
            "api_url": "https://api.test/occ/v2",
            "site": "en",
            "sitemap_path": "",
            "product_path_pattern": "",
            "recertified_sku_prefix": "",
        }
    )
    assert plain.products_url == "https://api.test/occ/v2/en/products"
    recertified = offer_from_product(product("R0F29590"), RECERTIFIED, STORE, plain)
    new = offer_from_product(product("R0F29590"), PAGE, STORE, plain)
    assert recertified is not None and new is not None
    assert (recertified.mpn, recertified.condition, new.condition) == (
        "R0F29590",
        "manufacturer_recertified",
        "new",
    )
