import json
from pathlib import Path

import pytest

from collector.models import ScrapedOffer, Store
from collector.sources.sitemap import (
    EmbeddedData,
    SitemapSettings,
    embedded_items,
    js_string,
    mpn_for,
    offers_from_page,
    product_path,
    recheck_offer,
    the_page,
    why_no_offers,
    within,
    worth_fetching,
)
from tests.builders import CONDITION_RULES, listing, sitemap_settings

FIXTURES = Path(__file__).parents[1] / "fixtures/goharddrive"
BASE = "https://www.goharddrive.com"
# goHardDrive as disktracker seeds it.
STORE = Store("goharddrive", BASE, conditions=CONDITION_RULES)
GHD = SitemapSettings.of(
    sitemap_settings(product_path_pattern="-p/", free_shipping_marker="Help_FreeShipping")
)
# A sitemap store with nothing set: disktracker gives every setting, blank.
BLANK = sitemap_settings()


def page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="latin-1")


def test_only_product_pages_that_look_like_drives_are_worth_fetching() -> None:
    paths = [
        "/Avolusion-PRO-5X-12TB-USB-3-0-HDD-PC-Mac-XBOX-p/g03-1842-xf.htm",
        "/MaxDigital-500G-8MB-Cache-5900RPM-SATA-III-3-5-HDD-p/g01-1189.htm",
        "/Avolusion-PRO-5X-USB-3-0-HDD-Enclosure-Grey-p/g04-0435.htm",
        "/Dual-Bay-Docking-Station-for-4TB-drives-p/g04-0001.htm",
        "/ASUS-VE245H-Black-24-5ms-HDMI-Widescreen-TFT-LCD-p/g05-0001.htm",
        "/Sabrent-USB-3-0-SATA-Adapter-p/g04-0777.htm",
    ]
    # Most of this store's product paths name a capacity, so the one that does not is skipped
    # along with those merely for drives.
    assert worth_fetching(paths) == paths[:2]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.goHardDrive.com/X-2TB-p/g01-2130.htm", "/X-2TB-p/g01-2130.htm"),
        ("https://goharddrive.com/X-2TB-p/g01-2130.htm", "/X-2TB-p/g01-2130.htm"),
        ("https://www.goharddrive.com/SSD-Solid-State-Drive-s/239.htm", None),
        ("https://example.com/X-2TB-p/g01-2130.htm", None),
    ],
)
def test_product_path_recognises_this_stores_product_pages_however_written(
    url: str, expected: str | None
) -> None:
    assert product_path(url, BASE, GHD) == expected


def test_a_maker_drive_page_becomes_an_offer_under_its_manufacturer_mpn() -> None:
    url = f"{BASE}/Dell-HGST-HUS726T4TAL4205-4TB-12Gb-s-SAS-HDD-p/g01-2172-cr.htm"
    found = offers_from_page(page("hgst_refurbished_out_of_stock.htm"), url, STORE, GHD)
    assert found == [
        ScrapedOffer(
            source="goharddrive",
            url=url,
            title="Dell / HGST Ultrastar DC HC300 HUS726T4TAL4205 4TB 7200RPM 256MB Cache SAS"
            " 12Gb/s 3.5 Inch Enterprise Hard Drive (Refurbished)- w/3 Year Warranty",
            mpn="HUS726T4TAL4205",
            brand="Western Digital",
            condition="refurbished",
            capacity_gb=4000,
            item_price_cents=7999,
            in_stock=False,
            shipping_cents=None,
            specifications={
                "media_type": "hdd",
                "form_factor": "3_5",
                "interface": "sas",
                "intended_use": ["enterprise"],
            },
        )
    ]


def test_an_own_brand_drive_is_identified_by_the_stores_product_code_and_ships_free() -> None:
    [offer] = offers_from_page(
        page("maxdigital_own_brand.htm"), f"{BASE}/x-p/g01-1060.htm", STORE, GHD
    )
    assert (offer.mpn, offer.condition, offer.item_price_cents, offer.in_stock) == (
        "G01-1060",
        "new",
        11899,
        True,
    )
    assert offer.shipping_cents == 0


def test_a_page_for_something_that_is_not_a_drive_is_no_offer() -> None:
    enclosure = page("avolusion_enclosure.htm")
    assert offers_from_page(enclosure, f"{BASE}/x-p/g04-0435.htm", STORE, GHD) == []


def test_a_recheck_keeps_disktrackers_identity_and_reads_price_and_stock_from_the_page() -> None:
    known = listing(
        f"{BASE}/x-p/g01-2172-cr.htm",
        store="goharddrive",
        mpn="HUS726T4TAL4205",
        condition="refurbished",
    )
    assert recheck_offer(
        known, page("hgst_refurbished_out_of_stock.htm"), STORE, GHD
    ) == ScrapedOffer(
        source="goharddrive",
        url=f"{BASE}/x-p/g01-2172-cr.htm",
        title=known.title,
        mpn="HUS726T4TAL4205",
        condition="refurbished",
        capacity_gb=known.drive.capacity_gb,
        item_price_cents=7999,
        in_stock=False,
        shipping_cents=None,
    )


def test_a_gone_page_is_out_of_stock_with_no_new_price() -> None:
    offer = recheck_offer(listing(f"{BASE}/x-p/g01-0001.htm"), None, STORE, GHD)
    assert (offer.item_price_cents, offer.in_stock, offer.shipping_cents) == (None, False, None)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Western Digital RE WD2000FYYZ 2TB SATA3 Hard Drive", "WD2000FYYZ"),
        ("Avolusion PRO-5X (Grey) 12TB USB 3.0 External Hard Drive", "G01-1060"),
        ("MaxDigital 4TB 7200RPM 64MB Cache SATA III", "G01-1060"),
        ("MaxDigitalData 2TB 128MB Cache 5400RPM 2.5in", "G01-1060"),
        ("MDD 4TB 7200RPM 64MB Cache SATA 3.5 Hard Drive", "G01-1060"),
        ("WL 160GB 8MB Cache 5400RPM SATA 2.5 Hard Drive", "G01-1060"),
        ("White Label 1TB 7200RPM SATA 3.5 Hard Drive", "G01-1060"),
        ("Major Brand 240GB 2.5 inch SATA SSD", "G01-1060"),
        ("goHardDrive.com - White Label 500GB 10000RPM SATA 3.5 Hard Drive", "G01-1060"),
        ("goHardDrive.com -Generic WL 160GB 8MB Cache 5400RPM SATA2 Hard Drive", "G01-1060"),
        ("goHardDrive.com - Major Brand 240GB 2.5-inch SATA SSD", "G01-1060"),
        ("goHardDrive.com - Kingston SSDNow V300 Series 120GB 2.5-inch SSD", None),
        ("Seagate 2TB drive in a white label enclosure", None),
        ("Kingston 240GB SATA III 2.5 SSD", None),
        ("HPE P42575-004 PM1653 7.68TB SAS 12Gbps SFF SSD", None),
        ("Kioxia SDFU081DHB04T PM7-R 15.3TB SAS SSD", None),
        ("4TB 7200RPM SATA 3.5 Hard Drive", None),
        ("HGST Ultrastar 0F23001 6TB 7200RPM Hard Drive", None),
    ],
    ids=lambda value: str(value)[:30],
)
def test_a_drive_is_named_by_its_makers_mpn_or_for_the_stores_own_brands_its_code(
    title: str, expected: str | None
) -> None:
    assert mpn_for(title, f"{BASE}/Some-Drive-p/g01-1060.htm") == expected


@pytest.mark.parametrize(
    "title",
    [
        "SK Hynix HMAA8GR7AJR4N-XN 64GB 3200MHz DDR4 RDIMM RAM Memory",
        "Samsung M393A4K40DB3-CWE 32GB DDR4 Registered Server Memory",
        "Kingston 16GB SODIMM Laptop Memory",
        "Crucial 8GB RAM",
    ],
)
def test_a_memory_module_is_no_drive_for_all_it_has_a_capacity(title: str) -> None:
    tagged = f'<title>{title}</title><meta itemprop="price" content="49.99">'
    assert offers_from_page(tagged, f"{BASE}/x", STORE, SitemapSettings.of(BLANK)) == []
    path = "/" + title.replace(" ", "-")
    assert worth_fetching([path, "/Toshiba-DT01ACA200-2TB-SATA-Hard-Drive"]) == [
        "/Toshiba-DT01ACA200-2TB-SATA-Hard-Drive"
    ]


@pytest.mark.parametrize(
    "title",
    [
        "Seagate Exos 4TB 256MB Cache SATA Hard Drive",
        "Intel Optane Memory H10 512GB SSD",
        "Samsung 870 EVO 1TB V-NAND Flash Memory SSD",
    ],
)
def test_a_drive_that_mentions_memory_is_still_a_drive(title: str) -> None:
    tagged = f'<title>{title}</title><meta itemprop="price" content="49.99">'
    assert len(offers_from_page(tagged, f"{BASE}/x", STORE, SitemapSettings.of(BLANK))) == 1


def test_a_store_whose_product_urls_name_no_capacity_has_every_drive_page_fetched() -> None:
    paths = ["/product/big-drive", "/product/fast-drive", "/product/drive-enclosure", "/p/4tb"]
    assert worth_fetching(paths) == ["/product/big-drive", "/product/fast-drive", "/p/4tb"]


def test_without_a_marker_shipping_is_unknown() -> None:
    plain = SitemapSettings.of(BLANK)
    [offer] = offers_from_page(
        page("maxdigital_own_brand.htm"), f"{BASE}/x-p/g01-1060.htm", STORE, plain
    )
    assert (offer.mpn, offer.shipping_cents) == ("G01-1060", None)


def test_a_page_title_is_its_og_title_else_its_title() -> None:
    page_with_both = (
        '<title>goHardDrive.com - Drive</title><meta property="og:title" content="Drive 4TB" />'
    )
    assert the_page(page_with_both).title == "Drive 4TB"
    assert the_page("<title>Only &amp; title</title>").title == "Only & title"


def test_a_page_without_price_tags_is_read_from_its_json_ld_product() -> None:
    serverorbit = (FIXTURES.parent / "serverorbit/huh721010aln600_refurbished.htm").read_text()
    found = the_page(serverorbit)
    assert (found.title, found.price_cents, found.in_stock) == (
        "Western Digital HUH721010ALN600 Ultrastar HE10 10TB Refurbished",
        27400,
        True,
    )


def json_ld(product: object) -> str:
    return (
        '<script type="application/ld+json">{"@type": "BreadcrumbList", "offers": {"price": 1}}'
        '</script><script type="application/ld+json">not json</script>'
        f"<script type='application/ld+json'>{json.dumps(product)}</script>"
    )


@pytest.mark.parametrize(
    ("offers", "price_cents", "in_stock"),
    [
        ({"price": "274.50", "availability": "https://schema.org/InStock"}, 27450, True),
        ([{"price": 99, "availability": "https://schema.org/OutOfStock"}], 9900, False),
        ({"price": "Call us"}, None, False),
        ({"price": 0, "availability": "InStock"}, None, False),
        ({"price": "0.00", "availability": "InStock"}, None, False),
        ([], None, False),
        (None, None, False),
    ],
    ids=[
        "one offer",
        "sold out",
        "no number",
        "zero",
        "zero written out",
        "no offers",
        "nothing offered",
    ],
)
def test_json_ld_is_read_from_the_product_block_whatever_else_the_page_carries(
    offers: object, price_cents: int | None, in_stock: bool
) -> None:
    found = the_page(json_ld({"@type": "Product", "offers": offers}))
    assert (found.price_cents, found.in_stock) == (price_cents, in_stock)


@pytest.mark.parametrize(
    "described",
    [
        [{"@type": "WebPage"}, {"@type": "Product", "offers": {"price": 5}}],
        {"@graph": [{"@type": "Organization"}, {"@type": "Product", "offers": {"price": 5}}]},
    ],
    ids=["a list of things", "a graph of things"],
)
def test_a_product_described_among_other_things_is_read(described: object) -> None:
    assert the_page(json_ld(described)).price_cents == 500


@pytest.mark.parametrize(
    "described", [[{"@type": "WebPage"}], {"@graph": "nothing"}, "text", {"@graph": ["text"]}]
)
def test_json_ld_that_describes_no_product_gives_no_price(described: object) -> None:
    assert the_page(json_ld(described)).price_cents is None


def test_a_drive_is_in_the_condition_its_page_states_when_its_title_does_not_say() -> None:
    disctech = (FIXTURES.parent / "disctech/toshiba_mg07aca14tey.htm").read_text()
    url = "https://www.disctech.com/Toshiba-MG07ACA14TEY-HDEPW40SXB51-14TB-LFF-6Gbps-7.2K-512e-HDD-SATA"
    [offer] = offers_from_page(disctech, url, STORE, SitemapSettings.of(BLANK))
    assert (offer.title, offer.mpn, offer.brand, offer.condition, offer.item_price_cents) == (
        "Toshiba MG07ACA14TEY / HDEPW40SXB51 14TB LFF 6Gbps 7.2K 512e HDD SATA",
        "MG07ACA14TEY",
        "Toshiba",
        "refurbished",
        28999,
    )


@pytest.mark.parametrize(
    ("title", "stated", "condition"),
    [
        ("Exos 4TB", "https://schema.org/UsedCondition", "used"),
        ("Exos 4TB", "NewCondition", "new"),
        # What the title says comes first, as the condition rules are ordered.
        ("Exos 4TB Renewed", "https://schema.org/NewCondition", "refurbished"),
        ("Exos 4TB", "https://schema.org/DamagedCondition", "new"),
        ("Exos 4TB", 7, "new"),
    ],
)
def test_the_condition_a_page_states_is_read_by_the_condition_rules(
    title: str, stated: object, condition: str
) -> None:
    page_text = f"<title>{title}</title>" + json_ld(
        {"@type": "Product", "offers": {"price": 5, "itemCondition": stated}}
    )
    [offer] = offers_from_page(page_text, f"{BASE}/x", STORE, SitemapSettings.of(BLANK))
    assert offer.condition == condition


def test_the_part_number_and_maker_a_page_states_are_read_from_its_json_ld() -> None:
    serverorbit = (FIXTURES.parent / "serverorbit/huh721010aln600_refurbished.htm").read_text()
    found = the_page(serverorbit)
    assert (found.model, found.brand) == ("HUH721010ALN600", "Western Digital")


@pytest.mark.parametrize(
    ("title", "product", "model"),
    [
        # A maker's MPN in the title is the surest; what the page states comes after it.
        ("Seagate ST4000NM000A 4TB", {"sku": "ST4000NM000A-R", "mpn": "OTHER-1"}, "ST4000NM000A"),
        ("Kioxia PM7-R 4TB", {"mpn": "SDFU081DHB04T", "sku": "200144"}, "SDFU081DHB04T"),
        ("Kioxia SDFU081DHB04T 4TB", {"sku": "sdfu081dhb04t"}, "sdfu081dhb04t"),
        # A SKU the title does not have is the store's own number, not the part's.
        ("Kioxia PM7-R 4TB", {"sku": "200144"}, None),
        # Too short to be told from any other text in a title.
        ("Kioxia PM7-R 4TB", {"sku": "4TB"}, None),
        ("Kioxia PM7-R 4TB", {"sku": 7, "mpn": None}, None),
        ("Kioxia PM7-R 4TB", {}, None),
    ],
    ids=["mpn in title", "mpn stated", "sku in title", "sku elsewhere", "short", "odd", "none"],
)
def test_a_page_is_one_product_with_the_part_number_its_title_or_its_json_ld_gives(
    title: str, product: dict[str, object], model: str | None
) -> None:
    page_text = f"<title>{title}</title>" + json_ld({"@type": "Product", **product})
    assert the_page(page_text).model == model


@pytest.mark.parametrize(
    ("brand", "read"),
    [({"@type": "Brand", "name": "Kioxia"}, "Kioxia"), ("Kioxia", "Kioxia"), (None, ""), (5, "")],
)
def test_the_maker_a_page_states_is_read_as_an_object_or_as_text(brand: object, read: str) -> None:
    page_text = "<title>Drive 4TB</title>" + json_ld({"@type": "Product", "brand": brand})
    assert the_page(page_text).brand == read


def test_price_tags_in_the_markup_are_read_before_json_ld() -> None:
    tagged = '<meta itemprop="price" content="10.00">' + json_ld(
        {"@type": "Product", "offers": {"price": 99, "availability": "InStock"}}
    )
    found = the_page(tagged)
    assert (found.price_cents, found.in_stock) == (1000, False)


def test_settings_are_read_as_disktracker_gives_them_so_a_missing_one_is_an_error() -> None:
    with pytest.raises(KeyError, match="sitemap_path"):
        SitemapSettings.of({"product_path_pattern": "-p/", "free_shipping_marker": ""})


FAMILY = SitemapSettings.of(
    sitemap_settings(
        data_pattern=r"models = JSON\.parse\('(.*?)'\);",
        data_items="*.skus.*",
        data_model_field="modelNo",
        data_name_field="name",
        data_price_field="final_price",
        data_brand_field="brand",
        data_stock_field="stock_status",
        data_in_stock_value="IN_STOCK",
    )
)
SEAGATE = Store("seagate", "https://www.seagate.com", conditions=CONDITION_RULES)
FAMILY_URL = "https://www.seagate.com/products/nas-drives/ironwolf-pro-hard-drive/"


def family_page() -> str:
    return (FIXTURES.parent / "seagate/ironwolf_pro.htm").read_text()


def test_a_page_of_many_models_gives_an_offer_for_each_one_it_prices() -> None:
    found = offers_from_page(family_page(), FAMILY_URL, SEAGATE, FAMILY)
    assert len(found) == 8
    assert found[1] == ScrapedOffer(
        source="seagate",
        url=FAMILY_URL,
        title="IronWolf Pro 28TB",
        mpn="ST28000NT000",
        # The name does not say who made it; the data's brand field does.
        brand="Seagate",
        condition="new",
        capacity_gb=28000,
        item_price_cents=122999,
        in_stock=True,
        shipping_cents=None,
        specifications={"intended_use": ["nas"]},
    )
    assert [(offer.mpn, offer.in_stock) for offer in found[:1]] == [("ST32000NT000", False)]


def data_settings(**given: str) -> EmbeddedData:
    named = {
        "data_pattern": r"<script id=\"data\">(.*?)</script>",
        "data_name_field": "name",
        "data_model_field": "model",
        "data_price_field": "price",
        **{f"data_{name}": value for name, value in given.items()},
    }
    data = EmbeddedData.of(sitemap_settings(**named))
    assert data is not None
    return data


def embedded(products: object) -> str:
    return f'<script id="data">{json.dumps(products)}</script>'


def test_embedded_data_written_as_plain_json_is_read_with_stock_taken_from_the_price() -> None:
    page_of_two = embedded(
        [{"name": "Drive 4TB", "model": " ab1 ", "price": 99.5}, {"name": "Call", "price": "POA"}]
    )
    assert [
        (item.title, item.model, item.price_cents, item.in_stock)
        for item in embedded_items(page_of_two, data_settings(items="*"))
    ] == [("Drive 4TB", "ab1", 9950, True), ("Call", None, None, False)]


def test_without_a_path_to_the_items_the_data_is_one_product() -> None:
    [item] = embedded_items(embedded({"name": "Drive 4TB", "price": "5"}), data_settings())
    assert (item.title, item.price_cents) == ("Drive 4TB", 500)


def test_the_maker_is_the_one_the_name_gives_else_the_one_the_brand_field_gives() -> None:
    products = embedded(
        [
            {"name": "Toshiba N300 4TB", "model": "A", "price": 1, "by": "seagate"},
            {"name": "Exos 4TB", "model": "B", "price": 1, "by": "seagate"},
            {"name": "Exos 8TB", "model": "C", "price": 1, "by": "Somebody"},
            {"name": "Exos 2TB", "model": "D", "price": 1},
        ]
    )
    settings = SitemapSettings.of(
        sitemap_settings(
            data_pattern=r"<script id=\"data\">(.*?)</script>",
            data_items="*",
            data_model_field="model",
            data_name_field="name",
            data_price_field="price",
            data_brand_field="by",
        )
    )
    found = offers_from_page(products, FAMILY_URL, SEAGATE, settings)
    assert [offer.brand for offer in found] == ["Toshiba", "Seagate", None, None]


def test_fields_can_be_paths_into_each_product() -> None:
    nested = embedded({"products": [{"name": "Drive 4TB", "model": "AB1", "offer": {"usd": "5"}}]})
    [item] = embedded_items(nested, data_settings(items="products.*", price_field="offer.usd"))
    assert item.price_cents == 500


@pytest.mark.parametrize(
    "page_text",
    ["<p>nothing here</p>", '<script id="data">{not json</script>'],
    ids=["no data", "data that is not JSON"],
)
def test_a_page_without_readable_data_offers_nothing(page_text: str) -> None:
    assert embedded_items(page_text, data_settings()) == []


def test_a_data_pattern_must_say_where_the_data_is() -> None:
    with pytest.raises(ValueError, match="data_pattern needs a group"):
        SitemapSettings.of(sitemap_settings(data_pattern="models = "))


def test_a_javascript_string_is_read_as_the_script_would_read_it() -> None:
    written = r"it\'s \"a\" \\u003d \x41\u0042 \n"
    assert js_string(written) == 'it\'s "a" \\u003d AB \n'


def test_a_path_leads_through_objects_and_every_entry_of_lists() -> None:
    data = [{"skus": [{"id": 1}, {"id": 2}]}, {"skus": {"a": {"id": 3}}}, "text"]
    assert within(data, "*.skus.*.id") == [1, 2, 3]
    assert within(data, "") == [data]
    assert within(data, "*.missing") == []


def test_a_recheck_on_a_page_of_many_reads_the_offers_own_model() -> None:
    known = listing(FAMILY_URL, store="seagate", mpn="ST8000NT001", condition="new")
    gone = listing(FAMILY_URL, store="seagate", mpn="ST9999NT001", condition="new")
    rechecked = recheck_offer(known, family_page(), SEAGATE, FAMILY)
    missing = recheck_offer(gone, family_page(), SEAGATE, FAMILY)
    assert (rechecked.item_price_cents, rechecked.in_stock) == (31999, True)
    assert (missing.item_price_cents, missing.in_stock) == (None, False)


@pytest.mark.parametrize(
    ("title", "price", "why"),
    [
        ("Some 4TB Drive", "", "no price (Some 4TB Drive)"),
        ("Some Drive", "9.99", "no capacity in its name (Some Drive)"),
        ("4TB Drive Enclosure", "9.99", "named as an accessory (4TB Drive Enclosure)"),
    ],
)
def test_a_page_that_is_no_drive_says_why(title: str, price: str, why: str) -> None:
    tagged = f'<title>{title}</title><meta itemprop="price" content="{price}">'
    assert why_no_offers(tagged, SitemapSettings.of(BLANK)) == why


def test_a_page_of_many_says_how_many_products_it_has_and_why_none_is_a_drive() -> None:
    settings = SitemapSettings.of(
        sitemap_settings(
            data_pattern=r"<script id=\"data\">(.*?)</script>",
            data_items="*",
            data_model_field="model",
            data_name_field="name",
            data_price_field="price",
        )
    )
    products = embedded(
        [{"name": "Drive 4TB"}, {"name": "Drive 8TB"}, {"name": "Cable", "price": 5}]
    )
    assert why_no_offers(products, settings) == (
        "3 products in its data: 2 with no price, 1 with no capacity in its name"
    )
    assert why_no_offers("<p>no data</p>", settings) == (
        "its data pattern or products path matched nothing"
    )


def test_a_price_tag_of_nothing_is_no_price() -> None:
    tagged = '<title>Drive 4TB</title><meta itemprop="price" content="0.00">'
    assert the_page(tagged).price_cents is None


def test_a_product_its_data_prices_at_nothing_has_no_price() -> None:
    [item] = embedded_items(
        embedded([{"name": "Drive 4TB", "model": "AB1", "price": "0.00"}]),
        data_settings(items="*"),
    )
    assert (item.price_cents, item.in_stock) == (None, False)
