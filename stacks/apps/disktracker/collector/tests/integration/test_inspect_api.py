"""Inspecting a link: given one product page of a store disktracker does not read yet, the
collector says which kind of source would read it and with what settings, and shows the offer
those settings read from that page. Nothing is kept.

These are also the backtests: each store disktracker already reads, inspected from one of its
own product pages, must be given the settings it was set up with by hand."""

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from pytest_httpserver import HTTPServer

from tests.builders import sitemap_settings
from tests.integration.conftest import echo
from tests.integration.harness import (
    ROOT,
    SEEDED_CONDITION_RULES,
    base_of,
    environment,
    know_listings,
    record_everything,
    run,
    serve_robots,
    source_json,
)
from tests.integration.test_browser_transport_run import VIA, serve_browser
from tests.integration.test_preview_api import CollectorApi, start_api

FIXTURES = ROOT / "tests/fixtures"


@pytest.fixture
def api(disktracker: HTTPServer) -> Iterator[CollectorApi]:
    running = start_api(disktracker)
    yield running
    if running.process.poll() is None:
        running.stop()


def inspect(api: CollectorApi, url: str) -> dict[str, Any]:
    answer = httpx.post(
        f"{api.url}/inspect", json={"url": url, "conditions": SEEDED_CONDITION_RULES}, timeout=30
    )
    assert answer.status_code == 200, answer.text
    inspected: dict[str, Any] = answer.json()
    return inspected


def serve_sitemap(store: HTTPServer, paths: list[str], at: str = "/sitemap.xml") -> None:
    base = base_of(store)
    entries = "".join(f"<url><loc>{base}{path}</loc></url>" for path in paths)
    store.expect_request(at).respond_with_data(
        f"<urlset>{entries}</urlset>", content_type="text/xml"
    )


def test_seagate_is_a_sitemap_source_read_from_the_data_its_pages_carry(
    api: CollectorApi, seagate: HTTPServer
) -> None:
    page = "/products/nas-drives/ironwolf-pro-hard-drive/"
    base = base_of(seagate)
    # As Seagate's robots.txt does, it names an index of every country's sitemap.
    serve_robots(seagate, f"User-agent: *\nDisallow:\nSitemap: {base}/siteindex.xml\n")
    serve_sitemap(
        seagate,
        [
            "/products/",
            page,
            "/products/enterprise-drives/exos/",
            "/support/kb/how-to-format-a-drive/",
            "/manuals/lacie/rugged/",
            "/news/news-archive/a-press-release/",
        ],
    )
    seagate.expect_request(page).respond_with_data(
        (FIXTURES / "seagate/ironwolf_pro.htm").read_text(), content_type="text/html"
    )

    inspected = inspect(api, f"{base}{page}")

    assert (inspected["status"], inspected["base_url"]) == ("found", base)
    [candidate] = inspected["candidates"]
    assert candidate["kind"] == "sitemap"
    # The settings it was given by hand.
    assert candidate["settings"] == sitemap_settings(
        sitemap_path="/sitemap.xml",
        product_path_pattern="^/products/",
        data_pattern=r"product_models = JSON\.parse\('(.*?)'\);",
        data_items="*.skus.*",
        data_model_field="modelNo",
        data_name_field="name",
        data_price_field="final_price",
        data_brand_field="brand",
        data_stock_field="stock_status",
        data_in_stock_value="IN_STOCK",
    )
    assert candidate["offers"] == 8
    assert (candidate["offer"]["mpn"], candidate["offer"]["brand"]) == ("ST32000NT000", "Seagate")
    # Only what the store was asked for: the page, and the one sitemap, not the whole index.
    assert [request.path for request, _ in seagate.log] == ["/robots.txt", page, "/sitemap.xml"]


def test_serverorbit_is_a_sitemap_source_read_from_each_pages_own_markup(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    page = "/cheap-western-digital-ultrastar-he10-huh721010aln600-10tb-7-2k-rpm-sata-6gbps/"
    serve_robots(serverorbit)
    serve_sitemap(
        serverorbit,
        [page, "/hard-disk-drives/", "/cisco-catalyst-9300-48-port-switch/", "/contacts/"],
    )
    serverorbit.expect_request(page).respond_with_data(
        (FIXTURES / "serverorbit/huh721010aln600_refurbished.htm").read_text(),
        content_type="text/html",
    )

    inspected = inspect(api, f"{base_of(serverorbit)}{page}")

    [candidate] = inspected["candidates"]
    # Nothing to set: its pages sit at the top of the store with nothing in common to match.
    assert (candidate["kind"], candidate["settings"]) == ("sitemap", sitemap_settings())
    assert (
        candidate["offers"],
        candidate["offer"]["mpn"],
        candidate["offer"]["item_price_cents"],
    ) == (
        1,
        "HUH721010ALN600",
        27400,
    )
    no_pattern = (
        "No product path pattern could be worked out from this page's address: every page"
        " the sitemap lists would be read."
    )
    assert candidate["evidence"] == [
        "The page gives its price as a JSON-LD Product.",
        "The page is in the store's sitemap, /sitemap.xml, which lists 4 pages.",
        no_pattern,
    ]


def test_goharddrive_is_a_sitemap_source_whose_product_pages_share_a_path(
    api: CollectorApi, goharddrive: HTTPServer
) -> None:
    page = "/DELL-Seagate-ST1000NM0023-1TB-7200RPM-SAS-HDD-p/g01-2130.htm"
    serve_robots(goharddrive)
    serve_sitemap(
        goharddrive,
        [
            page,
            "/MaxDigital-4TB-64MB-Cache-SATA3-3-5-Hard-Drive-p/g01-1060.htm",
            "/Avolusion-PRO-5X-USB-3-0-HDD-Enclosure-Grey-p/g04-0435.htm",
            "/SSD-Solid-State-Drive-s/239.htm",
            "/Hard-Drives-s/12.htm",
        ],
    )
    goharddrive.expect_request(page).respond_with_data(
        (FIXTURES / "goharddrive/maker_in_stock.htm").read_text(encoding="latin-1"),
        content_type="text/html; charset=ISO-8859-1",
    )

    inspected = inspect(api, f"{base_of(goharddrive)}{page}")

    [candidate] = inspected["candidates"]
    assert candidate["settings"] == sitemap_settings(product_path_pattern="-p/")
    assert candidate["offer"]["mpn"] == "ST1000NM0023"
    assert candidate["evidence"] == [
        "The page gives its price in schema.org tags in its markup.",
        "The page is in the store's sitemap, /sitemap.xml, which lists 5 pages.",
        "3 of them match the product path pattern -p/.",
    ]


def test_disctech_is_a_sitemap_source_whose_products_sit_at_the_top_of_the_store(
    disktracker: HTTPServer, serverorbit: HTTPServer
) -> None:
    # A collector that, as deployed, leaves two seconds between its requests to a store.
    api = start_api(disktracker, COLLECTOR_MIN_DELAY_SECONDS="2")
    page = "/Toshiba-MG07ACA14TEY-HDEPW40SXB51-14TB-LFF-6Gbps-7.2K-512e-HDD-SATA"
    base = base_of(serverorbit)
    # As DiscTech's robots.txt does, it names an index, whose one sitemap is /sitemap.xml.
    serve_robots(serverorbit, f"User-agent: *\nDisallow:\nSitemap: {base}/sitemapindex.xml\n")
    serve_sitemap(
        serverorbit,
        [
            "/",
            page,
            "/Toshiba-DT01ACA200-2TB-SATA-Hard-Drive",
            "/SK-Hynix-HMAA8GR7AJR4N-XN-64GB-3200MHz-DDR4-RDIMM-RAM-Memory",
            "/data-storage/internal-storage/sata-hard-drives",
            "/data-storage/internal-storage/sata-hard-drives/capacity/8TB/speed-disk-rpm/7.2K-RPM",
        ],
    )
    serverorbit.expect_request(page).respond_with_data(
        (FIXTURES / "disctech/toshiba_mg07aca14tey.htm").read_text(), content_type="text/html"
    )

    inspected = inspect(api, f"{base}{page}?gad_source=1&gclid=EAIaIQobChMI")

    [candidate] = inspected["candidates"]
    # Its products are the pages one part deep; its categories lie deeper.
    assert candidate["settings"] == sitemap_settings(
        sitemap_path="/sitemap.xml", product_path_pattern="^/[^/]+/?$"
    )
    offer = candidate["offer"]
    # All of it from the page's JSON-LD, where the product is one of several things described;
    # that it is refurbished is said only there, not in its title.
    assert {
        name: offer[name]
        for name in ("mpn", "brand", "condition", "capacity_gb", "item_price_cents", "in_stock")
    } == {
        "mpn": "MG07ACA14TEY",
        "brand": "Toshiba",
        "condition": "refurbished",
        "capacity_gb": 14000,
        "item_price_cents": 28999,
        "in_stock": True,
    }
    assert candidate["evidence"][2] == "3 of them match the product path pattern ^/[^/]+/?$."
    # How much there is to the store, to judge whether it is worth collecting: of its three
    # product pages one is a memory module, which a run would not fetch.
    assert candidate["summary"] == [
        {"label": "Pages in the sitemap", "value": "6"},
        {"label": "Product pages", "value": "3"},
        {"label": "Pages a run would fetch", "value": "2"},
        {"label": "Time for a run", "value": "under a minute (3 requests, 2 seconds apart)"},
    ]
    api.stop()


def test_a_run_with_the_suggested_settings_fetches_the_pages_the_summary_counted(
    disktracker: HTTPServer, goharddrive: HTTPServer
) -> None:
    page = "/DELL-Seagate-ST1000NM0023-1TB-7200RPM-SAS-HDD-p/g01-2130.htm"
    drives = [page, "/A-4TB-Drive-p/g01-0002.htm", "/B-8TB-Drive-p/g01-0003.htm"]
    serve_robots(goharddrive)
    serve_sitemap(
        goharddrive,
        [
            *drives,
            "/A-4TB-Drive-Enclosure-p/g04-0001.htm",
            "/Kingston-16GB-DDR4-RAM-p/g06-0001.htm",
            "/A-Drive-With-No-Capacity-Named-p/g01-0004.htm",
            "/Hard-Drives-s/12.htm",
        ],
    )
    for path in drives:
        goharddrive.expect_request(path).respond_with_data(
            (FIXTURES / "goharddrive/maker_in_stock.htm").read_text(encoding="latin-1"),
            content_type="text/html; charset=ISO-8859-1",
        )
    base = base_of(goharddrive)
    api = start_api(disktracker)
    [candidate] = inspect(api, f"{base}{page}")["candidates"]
    api.stop()
    counted = {fact["label"]: fact["value"] for fact in candidate["summary"]}
    inspected = len(goharddrive.log)
    # The fake disktracker told the inspecting collector nothing was due; it starts again.
    disktracker.clear()
    disktracker.expect_request("/api/collector-runs", method="POST").respond_with_handler(echo)
    record_everything(disktracker)
    know_listings(disktracker, [], store="goharddrive")

    result = run(
        environment(disktracker, source_json("goharddrive", "sitemap", base, candidate["settings"]))
    )

    assert result.returncode == 0, result.stderr
    fetched = [request.path for request, _ in goharddrive.log[inspected:]]
    # robots.txt and the sitemap, then exactly the pages the inspection said a run would fetch.
    assert fetched == ["/robots.txt", "/sitemap.xml", *drives]
    assert counted["Pages a run would fetch"] == str(len(drives))
    assert counted["Product pages"] == "6"


def test_the_summary_goes_by_the_delay_the_store_asks_for_and_says_how_fresh_its_sitemap_is(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    page = "/huh721010aln600-10tb/"
    base = base_of(serverorbit)
    # The store asks for a second between requests: more than this collector leaves by itself.
    serve_robots(serverorbit, "User-agent: *\nCrawl-delay: 1\n")
    entries = "".join(
        f"<url><loc>{base}{path}</loc><lastmod>{changed}</lastmod></url>"
        for path, changed in [
            (page, "2026-06-26T10:00:00+00:00"),
            ("/another-4tb-drive/", "2026-09-30"),
            ("/a-third-8tb-drive/", "2025-01-02"),
        ]
    )
    serverorbit.expect_request("/sitemap.xml").respond_with_data(
        f"<urlset>{entries}</urlset>", content_type="text/xml"
    )
    serverorbit.expect_request(page).respond_with_data(
        (FIXTURES / "serverorbit/huh721010aln600_refurbished.htm").read_text(),
        content_type="text/html",
    )

    [candidate] = inspect(api, f"{base}{page}")["candidates"]

    assert candidate["summary"] == [
        {"label": "Pages in the sitemap", "value": "3"},
        {"label": "Product pages", "value": "3"},
        {"label": "Pages a run would fetch", "value": "3"},
        {"label": "Sitemap last changed", "value": "2026-09-30"},
        {"label": "Time for a run", "value": "under a minute (4 requests, 1 second apart)"},
    ]


def test_a_way_of_reading_the_page_is_kept_when_time_runs_out_looking_for_its_sitemap(
    disktracker: HTTPServer, serverorbit: HTTPServer
) -> None:
    page = "/huh721010aln600-10tb/"
    base = base_of(serverorbit)
    # A second between requests, and no sitemap where it is first looked for: by the time the
    # one robots.txt names would be asked for, the half second allowed is long gone.
    serve_robots(serverorbit, f"User-agent: *\nCrawl-delay: 1\nSitemap: {base}/products.xml\n")
    serverorbit.expect_request("/sitemap.xml").respond_with_data("", status=404)
    serverorbit.expect_request(page).respond_with_data(
        (FIXTURES / "serverorbit/huh721010aln600_refurbished.htm").read_text(),
        content_type="text/html",
    )
    api = start_api(disktracker, COLLECTOR_PREVIEW_SECONDS="0.5")

    inspected = inspect(api, f"{base}{page}")
    api.stop()

    [candidate] = inspected["candidates"]
    assert (inspected["status"], candidate["offer"]["mpn"]) == ("found", "HUH721010ALN600")
    assert candidate["settings"] == sitemap_settings()
    assert candidate["evidence"][1] == (
        "The store's sitemap was not found before time ran out (out of time after 0.5 seconds:"
        f" 2 requests made, the last for {base}/sitemap.xml), so its sitemap path and product"
        " path pattern are not worked out."
    )
    assert candidate["summary"] == []
    assert [request.path for request, _ in serverorbit.log] == ["/robots.txt", page, "/sitemap.xml"]


def test_a_store_that_answers_only_browsers_is_inspected_through_one(
    disktracker: HTTPServer, serverorbit: HTTPServer, flaresolverr: HTTPServer
) -> None:
    page = "/huh721010aln600-10tb/"
    serve_robots(serverorbit)
    serve_sitemap(serverorbit, [page])
    serverorbit.expect_request(page).respond_with_data(
        (FIXTURES / "serverorbit/huh721010aln600_refurbished.htm").read_text(),
        content_type="text/html",
    )
    api = start_api(disktracker, **serve_browser(flaresolverr))

    answer = httpx.post(
        f"{api.url}/inspect",
        json={"url": f"{base_of(serverorbit)}{page}", "transport": "browser"},
        timeout=30,
    )
    api.stop()

    [candidate] = answer.json()["candidates"]
    assert candidate["offer"]["mpn"] == "HUH721010ALN600"
    # Everything the store was asked for came from the browser.
    assert {request.headers.get(VIA) for request, _ in serverorbit.log} == {"flaresolverr"}
    assert [request.path for request, _ in serverorbit.log] == ["/robots.txt", page, "/sitemap.xml"]


def test_a_shopify_store_is_read_from_the_collection_its_link_names(
    api: CollectorApi, serverpartdeals: HTTPServer
) -> None:
    feed = json.loads((FIXTURES / "serverpartdeals_page1.json").read_text())
    linked = "/collections/hard-drives/products/wd-ultrastar-hc550-wuh721818ale6l4"
    serve_robots(serverpartdeals)
    serverpartdeals.expect_request(linked).respond_with_data(
        (FIXTURES / "shopify/product_page.htm").read_text(), content_type="text/html"
    )
    serverpartdeals.expect_request(
        "/collections/hard-drives/products.json", query_string="limit=250&page=1"
    ).respond_with_json({"products": feed["products"]})
    base = base_of(serverpartdeals)

    inspected = inspect(api, f"{base}{linked}")

    [candidate] = inspected["candidates"]
    assert (candidate["kind"], candidate["settings"]) == (
        "shopify",
        {"collections": ["hard-drives"], "free_shipping": False},
    )
    # Every offer on the collection's first page was read; the one the link is to is shown.
    assert (candidate["offers"], candidate["offer"]["mpn"], candidate["offer"]["url"]) == (
        3,
        "WUH721818ALE6L4",
        f"{base}/products/wd-ultrastar-hc550-wuh721818ale6l4",
    )
    assert candidate["evidence"] == [
        "The page is a Shopify store's.",
        "The link names the collection hard-drives; add any others that hold drives.",
    ]
    # The page, then one page of the collection: no sitemap is looked for.
    assert [request.path for request, _ in serverpartdeals.log] == [
        "/robots.txt",
        linked,
        "/collections/hard-drives/products.json",
    ]


def test_a_shopify_link_that_names_no_collection_is_given_the_whole_catalogue(
    api: CollectorApi, serverpartdeals: HTTPServer
) -> None:
    feed = json.loads((FIXTURES / "serverpartdeals_page1.json").read_text())
    serve_robots(serverpartdeals)
    serverpartdeals.expect_request("/products/a-drive-not-on-the-first-page").respond_with_data(
        (FIXTURES / "shopify/product_page.htm").read_text(), content_type="text/html"
    )
    serverpartdeals.expect_request(
        "/collections/all/products.json", query_string="limit=250&page=1"
    ).respond_with_json({"products": feed["products"]})

    inspected = inspect(api, f"{base_of(serverpartdeals)}/products/a-drive-not-on-the-first-page")

    [candidate] = inspected["candidates"]
    assert candidate["settings"] == {"collections": ["all"], "free_shipping": False}
    assert candidate["offer"]["mpn"] == "ST18000NM003D"
    whole = (
        "The link names no collection, so all, the store's whole catalogue, is suggested:"
        " narrow it to the collections that hold drives."
    )
    elsewhere = (
        "The linked product is not among the first 250 the collection lists; the first offer"
        " read is shown instead."
    )
    assert candidate["evidence"] == ["The page is a Shopify store's.", whole, elsewhere]


def test_the_way_that_reads_the_linked_drive_comes_before_one_that_reads_more_of_the_store(
    api: CollectorApi, serverpartdeals: HTTPServer
) -> None:
    # A Shopify store whose page also prices its drive in JSON-LD: both kinds read it. The
    # collection's first page has three offers, but not the linked drive; the page has it.
    feed = json.loads((FIXTURES / "serverpartdeals_page1.json").read_text())
    linked = "/products/huh721010aln600-10tb"
    page = (
        (FIXTURES / "serverorbit/huh721010aln600_refurbished.htm")
        .read_text()
        .replace("</head>", '<script src="//cdn.shopify.com/s/files/theme.js"></script></head>')
    )
    serve_robots(serverpartdeals)
    serverpartdeals.expect_request(linked).respond_with_data(page, content_type="text/html")
    serverpartdeals.expect_request("/collections/all/products.json").respond_with_json(
        {"products": feed["products"]}
    )
    serve_sitemap(serverpartdeals, [linked])

    inspected = inspect(api, f"{base_of(serverpartdeals)}{linked}")

    assert [
        (candidate["kind"], candidate["offers"], candidate["offer"]["mpn"])
        for candidate in inspected["candidates"]
    ] == [("sitemap", 1, "HUH721010ALN600"), ("shopify", 3, "ST18000NM003D")]


def test_a_shopify_store_whose_collection_cannot_be_read_is_no_way_to_read_it(
    api: CollectorApi, serverpartdeals: HTTPServer
) -> None:
    serve_robots(serverpartdeals)
    serverpartdeals.expect_request("/products/a-drive").respond_with_data(
        (FIXTURES / "shopify/product_page.htm").read_text(), content_type="text/html"
    )
    serverpartdeals.expect_request("/collections/all/products.json").respond_with_data(
        "", status=404
    )
    base = base_of(serverpartdeals)

    inspected = inspect(api, f"{base}/products/a-drive")

    assert (inspected["status"], inspected["candidates"]) == ("nothing", [])
    assert inspected["notes"][0].startswith(
        "It is a Shopify store, but its collection all could not be read:"
        f" Not found: {base}/collections/all/products.json"
    )


def test_a_shopify_store_whose_collection_holds_nothing_is_no_way_to_read_it(
    api: CollectorApi, serverpartdeals: HTTPServer
) -> None:
    serve_robots(serverpartdeals)
    serverpartdeals.expect_request("/products/a-drive").respond_with_data(
        (FIXTURES / "shopify/product_page.htm").read_text(), content_type="text/html"
    )
    serverpartdeals.expect_request("/collections/all/products.json").respond_with_json(
        {"products": []}
    )

    inspected = inspect(api, f"{base_of(serverpartdeals)}/products/a-drive")

    assert inspected["notes"][0] == "It is a Shopify store, but its collection all lists no drive."


def test_a_page_no_sitemap_lists_is_still_read_and_says_a_run_would_miss_it(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    page = "/huh721010aln600-10tb/"
    base = base_of(serverorbit)
    # No /sitemap.xml; robots.txt names an index, which is not followed, and a sitemap that
    # does not list the page.
    serve_robots(
        serverorbit,
        f"User-agent: *\nDisallow:\nSitemap: {base}/index.xml\nSitemap: {base}/other.xml\n",
    )
    serverorbit.expect_request("/sitemap.xml").respond_with_data("", status=404)
    serverorbit.expect_request("/index.xml").respond_with_data(
        f"<sitemapindex><sitemap><loc>{base}/a.xml</loc></sitemap></sitemapindex>"
    )
    serverorbit.expect_request(page).respond_with_data(
        (FIXTURES / "serverorbit/huh721010aln600_refurbished.htm").read_text(),
        content_type="text/html",
    )

    inspected = inspect(api, f"{base}{page}")

    [candidate] = inspected["candidates"]
    assert (candidate["settings"], candidate["offer"]["mpn"]) == (
        sitemap_settings(),
        "HUH721010ALN600",
    )
    unlisted = (
        "The page was not found in the store's sitemap, so a run would not read it: set the"
        " Sitemap path to the sitemap that lists it."
    )
    assert candidate["evidence"][1:] == [unlisted]
    # Two places are tried, and no more.
    assert [request.path for request, _ in serverorbit.log] == [
        "/robots.txt",
        page,
        "/sitemap.xml",
        "/index.xml",
    ]


def test_a_page_with_no_drive_to_read_says_what_was_looked_for(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    serve_robots(serverorbit)
    serverorbit.expect_request("/about/").respond_with_data(
        "<title>About us</title>", content_type="text/html"
    )

    inspected = inspect(api, f"{base_of(serverorbit)}/about/")

    assert (inspected["status"], inspected["candidates"]) == ("nothing", [])
    # Each kind of source says what it looked for.
    assert inspected["notes"] == [
        "The page loads nothing from Shopify, so the store is not one of its.",
        "No price was found in the page's markup, and it has no JSON-LD.",
        "No product data was found in the page's scripts.",
        "SAP Commerce stores are not recognised from a link yet.",
    ]


def test_data_that_names_drives_but_prices_none_of_them_is_not_a_way_to_read_the_page(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    serve_robots(serverorbit)
    products = [
        {"name": "Exos 4TB", "model": "ST4000NM000A"},
        {"name": "Drive cable", "model": "CAB-00001", "price": "5.00"},
    ]
    serverorbit.expect_request("/family/").respond_with_data(
        f"<title>Drives</title><script>x.models = JSON.parse('{json.dumps(products)}');</script>",
        content_type="text/html",
    )

    inspected = inspect(api, f"{base_of(serverorbit)}/family/")

    assert (inspected["status"], inspected["candidates"]) == ("nothing", [])
    assert inspected["notes"][2] == (
        "The data in the page's scripts gives no drive: 2 products in its data: 1 with no price,"
        " 1 with no capacity in its name."
    )


def test_a_page_whose_json_ld_describes_no_product_says_what_it_does_describe(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    serve_robots(serverorbit)
    described = {"@graph": [{"@type": "WebPage"}, {"@type": "Organization"}, {"@type": "WebPage"}]}
    serverorbit.expect_request("/drive/").respond_with_data(
        "<title>A 4TB drive</title>"
        f'<script type="application/ld+json">{json.dumps(described)}</script>',
        content_type="text/html",
    )

    inspected = inspect(api, f"{base_of(serverorbit)}/drive/")

    assert inspected["notes"][1] == (
        "No price was found in the page's markup, and its JSON-LD describes no product"
        " (it describes: WebPage, Organization)."
    )


def test_a_page_the_store_refuses_cannot_be_inspected(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    serve_robots(serverorbit)
    serverorbit.expect_request("/drive/").respond_with_data("blocked", status=403)
    url = f"{base_of(serverorbit)}/drive/"

    inspected = inspect(api, url)

    assert (inspected["status"], inspected["candidates"]) == ("failed", [])
    assert inspected["reason"].startswith("Client error '403 FORBIDDEN'")


def test_a_page_cannot_be_fetched_by_a_transport_there_is_not(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    answer = httpx.post(
        f"{api.url}/inspect",
        json={"url": f"{base_of(serverorbit)}/drive/", "transport": "carrier-pigeon"},
        timeout=30,
    )

    assert (answer.json()["status"], answer.json()["reason"]) == (
        "failed",
        "settings: pages cannot be fetched by carrier-pigeon",
    )
    assert serverorbit.log == []


def test_a_request_that_names_no_page_is_refused(api: CollectorApi) -> None:
    missing = httpx.post(f"{api.url}/inspect", json={}, timeout=30)
    not_a_page = httpx.post(f"{api.url}/inspect", json={"url": "seagate"}, timeout=30)

    assert (missing.status_code, missing.json()) == (422, {"detail": "missing url"})
    assert (not_a_page.status_code, not_a_page.json()) == (
        422,
        {"detail": "url is not a page's address"},
    )
