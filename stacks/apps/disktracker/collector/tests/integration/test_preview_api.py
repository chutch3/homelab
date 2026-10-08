"""The collector's API previews a source: it reads just enough of a store to show one offer,
keeps nothing, and never waits behind a scheduled run."""

import json
import signal
import socket
import subprocess
import threading
import time
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

from tests.builders import sitemap_settings
from tests.integration.harness import (
    ROOT,
    SEEDED_CONDITION_RULES,
    base_of,
    environment,
    events,
    serve_robots,
    source_json,
    start_loop,
)
from tests.integration.test_westerndigital_run import RED, wd_source
from tests.integration.test_westerndigital_run import ULTRASTAR as WD_ULTRASTAR
from tests.integration.test_westerndigital_run import serve_store as serve_westerndigital

PAGE = json.loads((ROOT / "tests/fixtures/serverpartdeals_page1.json").read_text())
GOHARDDRIVE = ROOT / "tests/fixtures/goharddrive"
SEAGATE = "/DELL-Seagate-ST1000NM0023-1TB-7200RPM-SAS-HDD-p/g01-2130.htm"
ENCLOSURE = "/Avolusion-PRO-5X-USB-3-0-HDD-Enclosure-Grey-p/g04-0435.htm"
SERVERORBIT = ROOT / "tests/fixtures/serverorbit"
ULTRASTAR = "/cheap-western-digital-ultrastar-he10-huh721010aln600-10tb-7-2k-rpm-sata-6gbps-256mb-enterprise-hdd/"
SHOPIFY = {"collections": ["hard-drives", "solid-state-drives"], "free_shipping": True}
SITEMAP = sitemap_settings(product_path_pattern="-p/")


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class CollectorApi:
    """A running collector and its API."""

    def __init__(self, process: subprocess.Popen[str], url: str) -> None:
        self.process, self.url = process, url

    def preview(self, **source: Any) -> httpx.Response:
        asked = {"key": "newstore", "transport": "direct", "conditions": SEEDED_CONDITION_RULES}
        return httpx.post(f"{self.url}/preview", json={**asked, **source}, timeout=30)

    def stop(self) -> list[dict[str, Any]]:
        """Stop it; what it logged."""
        self.process.send_signal(signal.SIGTERM)
        stdout, stderr = self.process.communicate(timeout=30)
        assert self.process.returncode == 0, stderr
        return events(stdout)


def start_api(disktracker: HTTPServer, *due: dict[str, Any], **settings: str) -> CollectorApi:
    port = free_port()
    env = environment(disktracker, *due, COLLECTOR_API_PORT=str(port), **settings)
    running = CollectorApi(start_loop(env), f"http://127.0.0.1:{port}")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{running.url}/health", timeout=1).status_code == 200:
                return running
        except httpx.HTTPError:
            time.sleep(0.05)
    raise AssertionError(f"the collector API never answered: {running.process.communicate()}")


@pytest.fixture
def api(disktracker: HTTPServer) -> Iterator[CollectorApi]:
    running = start_api(disktracker)
    yield running
    if running.process.poll() is None:
        running.stop()


def serve_shop(store: HTTPServer) -> None:
    serve_robots(store)
    store.expect_request("/collections/hard-drives/products.json").respond_with_json(
        {"products": PAGE["products"]}
    )


def serve_sitemap(store: HTTPServer, paths: list[str]) -> None:
    serve_robots(store)
    base = base_of(store)
    entries = "".join(f"<url><loc>{base}{path}</loc></url>" for path in paths)
    store.expect_request("/sitemap.xml").respond_with_data(
        f"<urlset>{entries}</urlset>", content_type="text/xml"
    )
    store.expect_request(SEAGATE).respond_with_data(
        (GOHARDDRIVE / "maker_in_stock.htm").read_text(encoding="latin-1"),
        content_type="text/html; charset=ISO-8859-1",
    )


def test_a_shopify_preview_reads_one_page_and_shows_its_first_offer_without_saving_it(
    api: CollectorApi, serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_shop(serverpartdeals)
    base = base_of(serverpartdeals)

    answer = api.preview(kind="shopify", base_url=base, settings=SHOPIFY)

    assert answer.status_code == 200, answer.text
    assert answer.json() == {
        "status": "found",
        "reason": None,
        "offer": {
            "source": "newstore",
            "url": f"{base}/products/seagate-exos-x20-st18000nm003d-18tb",
            "title": PAGE["products"][0]["title"],
            "mpn": "ST18000NM003D",
            "condition": "manufacturer_recertified",
            "capacity_gb": 18000,
            "item_price_cents": 51900,
            "in_stock": True,
            "seller": "",
            "shipping_cents": 0,
            "aliases": [],
            "specifications": {
                "media_type": "hdd",
                "form_factor": "3_5",
                "interface": "sata",
                "intended_use": ["enterprise"],
            },
            "brand": "Seagate",
        },
        "notes": [],
    }
    # One page of the first collection, and nothing told to disktracker.
    assert [
        (request.path, request.query_string.decode()) for request, _ in serverpartdeals.log
    ] == [("/robots.txt", ""), ("/collections/hard-drives/products.json", "limit=250&page=1")]
    api.stop()
    assert [request.path for request, _ in disktracker.log if request.method == "POST"] == []


def test_a_sitemap_preview_stops_at_the_first_drive(
    api: CollectorApi, goharddrive: HTTPServer
) -> None:
    serve_sitemap(goharddrive, [SEAGATE, "/Another-2TB-Drive-p/g01-0002.htm"])

    answer = api.preview(kind="sitemap", base_url=base_of(goharddrive), settings=SITEMAP)

    found = answer.json()
    assert (found["status"], found["offer"]["mpn"]) == ("found", "ST1000NM0023")
    assert [request.path for request, _ in goharddrive.log] == [
        "/robots.txt",
        "/sitemap.xml",
        SEAGATE,
    ]


def test_a_sitemap_preview_reads_a_page_that_gives_its_price_as_json_ld(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    # ServerOrbit (CS-Cart) tags nothing in its markup: price and stock are in a JSON-LD block.
    serve_robots(serverorbit)
    base = base_of(serverorbit)
    serverorbit.expect_request("/sitemap.xml").respond_with_data(
        f"<urlset><url><loc>{base}{ULTRASTAR}</loc></url></urlset>", content_type="text/xml"
    )
    serverorbit.expect_request(ULTRASTAR).respond_with_data(
        (SERVERORBIT / "huh721010aln600_refurbished.htm").read_text(), content_type="text/html"
    )

    answer = api.preview(
        kind="sitemap", base_url=base, settings={**SITEMAP, "product_path_pattern": ""}
    )

    found = answer.json()
    assert found["status"] == "found", found
    offer = found["offer"]
    assert {name: offer[name] for name in ("mpn", "condition", "capacity_gb")} == {
        "mpn": "HUH721010ALN600",
        "condition": "refurbished",
        "capacity_gb": 10000,
    }
    assert (offer["item_price_cents"], offer["in_stock"]) == (27400, True)


def test_a_drive_whose_title_has_no_readable_mpn_takes_the_part_number_its_page_states(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    # A maker whose part numbers disktracker cannot tell from a title: the page's JSON-LD
    # names the part as its SKU, and the title has that same text.
    kioxia = "/kioxia-sdfu081dhb04t-pm7-r-series-10tb-sas-24gbps-enterprise-ssd/"
    page = (
        (SERVERORBIT / "huh721010aln600_refurbished.htm")
        .read_text()
        .replace("HUH721010ALN600", "SDFU081DHB04T")
        .replace("Western Digital", "Kioxia")
        .replace("Ultrastar HE10", "PM7-R")
    )
    serve_robots(serverorbit)
    serverorbit.expect_request(kioxia).respond_with_data(page, content_type="text/html")
    base = base_of(serverorbit)

    answer = api.preview(
        kind="sitemap", base_url=base, settings=sitemap_settings(), page_url=f"{base}{kioxia}"
    )

    found = answer.json()
    assert found["status"] == "found", found
    assert (found["offer"]["title"], found["offer"]["mpn"]) == (
        "Kioxia SDFU081DHB04T PM7-R 10TB Refurbished",
        "SDFU081DHB04T",
    )


def test_a_page_that_prices_its_drive_at_nothing_has_no_price(
    api: CollectorApi, serverorbit: HTTPServer
) -> None:
    # ServerOrbit writes a price of 0 for a drive it sells only by quote.
    quoted = "/seagate-st18000nm0092-exos-2x18-18tb/"
    page = (SERVERORBIT / "huh721010aln600_refurbished.htm").read_text()
    assert '"price":274,' in page
    serve_robots(serverorbit)
    serverorbit.expect_request(quoted).respond_with_data(
        page.replace('"price":274,', '"price":0,'), content_type="text/html"
    )
    base = base_of(serverorbit)

    answer = api.preview(
        kind="sitemap", base_url=base, settings=sitemap_settings(), page_url=f"{base}{quoted}"
    )

    title = "Western Digital HUH721010ALN600 Ultrastar HE10 10TB Refurbished"
    assert answer.json() == {
        "status": "nothing",
        "reason": None,
        "offer": None,
        "notes": [f"{base}{quoted}: no price ({title})"],
    }


def test_a_sap_commerce_preview_reads_the_first_product_its_sitemap_lists(
    api: CollectorApi, westerndigital: HTTPServer
) -> None:
    serve_westerndigital(westerndigital, [RED, WD_ULTRASTAR])
    source = wd_source(westerndigital)

    answer = api.preview(
        kind=source["kind"], base_url=source["base_url"], settings=source["settings"]
    )

    found = answer.json()
    assert (found["status"], found["offer"]["mpn"]) == ("found", "WD120EFBX")
    # It stops at the first offer: the second product is not asked for.
    assert [request.path for request, _ in westerndigital.log] == [
        "/robots.txt",
        "/products-sitemap.xml",
        "/wdwebservices/v2/us/products/WD120EFBX",
    ]


def test_a_preview_that_finds_no_drive_says_so(api: CollectorApi, goharddrive: HTTPServer) -> None:
    serve_sitemap(goharddrive, [ENCLOSURE])

    answer = api.preview(kind="sitemap", base_url=base_of(goharddrive), settings=SITEMAP)

    # What it read is told, so the settings can be put right.
    assert answer.json() == {
        "status": "nothing",
        "reason": None,
        "offer": None,
        "notes": ["The sitemap lists 1 page; 0 are product pages to read."],
    }


def test_a_preview_says_why_each_page_it_read_gave_no_drive(
    api: CollectorApi, goharddrive: HTTPServer
) -> None:
    unpriced = "/Some-4TB-Drive-p/g01-0009.htm"
    serve_sitemap(goharddrive, [unpriced, "/Gone-2TB-Drive-p/g01-0010.htm"])
    goharddrive.expect_request(unpriced).respond_with_data(
        "<title>Some 4TB Drive</title>", content_type="text/html"
    )
    base = base_of(goharddrive)

    answer = api.preview(kind="sitemap", base_url=base, settings=SITEMAP)

    gone = f"{base}/Gone-2TB-Drive-p/g01-0010.htm"
    refused = (
        f"Server error '500 INTERNAL SERVER ERROR' for url '{gone}'\n"
        "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500"
    )
    assert answer.json()["notes"] == [
        "The sitemap lists 2 pages; 2 are product pages to read.",
        f"{base}{unpriced}: no price (Some 4TB Drive)",
        f"{gone}: could not be fetched ({refused})",
    ]


SEAGATE_PAGE = "/products/nas-drives/ironwolf-pro-hard-drive/"
FAMILY = sitemap_settings(
    product_path_pattern="^/products/",
    data_pattern=r"product_models = JSON\.parse\('(.*?)'\);",
    data_items="*.skus.*",
    data_model_field="modelNo",
    data_name_field="name",
    data_price_field="final_price",
)


def test_a_preview_of_one_page_reads_that_page_and_not_the_sitemap(
    api: CollectorApi, seagate: HTTPServer
) -> None:
    serve_robots(seagate)
    seagate.expect_request(SEAGATE_PAGE).respond_with_data(
        (ROOT / "tests/fixtures/seagate/ironwolf_pro.htm").read_text(), content_type="text/html"
    )
    base = base_of(seagate)

    answer = api.preview(
        kind="sitemap", base_url=base, settings=FAMILY, page_url=f"{base}{SEAGATE_PAGE}"
    )

    found = answer.json()
    assert (found["status"], found["offer"]["mpn"], found["notes"]) == ("found", "ST32000NT000", [])
    assert [request.path for request, _ in seagate.log] == ["/robots.txt", SEAGATE_PAGE]


def test_a_page_to_preview_must_be_on_the_store(api: CollectorApi, seagate: HTTPServer) -> None:
    answer = api.preview(
        kind="sitemap",
        base_url=base_of(seagate),
        settings=FAMILY,
        page_url="https://elsewhere.test/products/drive/",
    )

    failed = answer.json()
    assert (failed["status"], failed["reason"]) == (
        "failed",
        "settings: the page to test is not on this store",
    )
    assert seagate.log == []


def test_a_preview_stops_when_its_time_is_up_and_says_how_far_it_got(
    disktracker: HTTPServer, seagate: HTTPServer
) -> None:
    # A store that asks for a second between requests, with an index of more sitemaps than a
    # preview has time for.
    base = base_of(seagate)
    serve_robots(seagate, f"User-agent: *\nCrawl-delay: 1\nSitemap: {base}/siteindex.xml\n")
    nested = [f"/{country}-sitemap.xml" for country in ("us", "de", "fr", "gb", "jp", "kr")]
    index = "".join(f"<sitemap><loc>{base}{path}</loc></sitemap>" for path in nested)
    seagate.expect_request("/siteindex.xml").respond_with_data(
        f"<sitemapindex>{index}</sitemapindex>", content_type="text/xml"
    )
    for path in nested:
        seagate.expect_request(path).respond_with_data("<urlset></urlset>", content_type="text/xml")
    running = start_api(disktracker, COLLECTOR_PREVIEW_SECONDS="1.5")

    answer = running.preview(kind="sitemap", base_url=base, settings=FAMILY)
    running.stop()

    failed = answer.json()
    asked = [request.path for request, _ in seagate.log]
    assert failed["status"] == "failed"
    assert failed["reason"] == (
        f"out of time after 1.5 seconds: {len(asked) - 1} requests made, the last for"
        f" {base}{asked[-1]}"
    )
    assert 3 <= len(asked) < len(nested) + 2, asked


@pytest.mark.parametrize(
    ("source", "robots", "reason"),
    [
        ({"kind": "shopify", "settings": {}}, None, "settings: missing collections"),
        ({"kind": "manual", "settings": {}}, None, "settings: a manual source is not collected"),
        (
            {"kind": "shopify", "settings": SHOPIFY, "transport": "vpn"},
            None,
            "settings: pages cannot be fetched by vpn",
        ),
        (
            {"kind": "shopify", "settings": SHOPIFY},
            "User-agent: *\nDisallow: /collections/\n",
            "robots.txt disallows",
        ),
        (
            {"kind": "shopify", "settings": SHOPIFY, "page_url": "PAGE"},
            None,
            "settings: this kind of store cannot be tested on one page",
        ),
    ],
    ids=[
        "a setting left out",
        "a store entered by hand",
        "no such transport",
        "robots forbids",
        "a kind that reads no page alone",
    ],
)
def test_a_preview_that_cannot_be_read_gives_the_reason(
    api: CollectorApi,
    serverpartdeals: HTTPServer,
    source: dict[str, Any],
    robots: str | None,
    reason: str,
) -> None:
    if robots is not None:
        serve_robots(serverpartdeals, robots)

    base = base_of(serverpartdeals)
    if "page_url" in source:
        source = {**source, "page_url": f"{base}/products/a-drive"}
    answer = api.preview(base_url=base, **source)

    failed = answer.json()
    assert answer.status_code == 200, answer.text
    assert (failed["status"], failed["offer"]) == ("failed", None)
    assert failed["reason"].startswith(reason)


def test_every_preview_reads_robots_txt_afresh_so_a_refusal_is_not_remembered(
    api: CollectorApi, serverpartdeals: HTTPServer
) -> None:
    # The store refuses the first request for robots.txt, and answers the next.
    serverpartdeals.expect_oneshot_request("/robots.txt").respond_with_data("no", status=403)
    serve_shop(serverpartdeals)
    source = {"kind": "shopify", "base_url": base_of(serverpartdeals), "settings": SHOPIFY}

    refused = api.preview(**source).json()
    again = api.preview(**source).json()

    assert (refused["status"], again["status"]) == ("failed", "found")
    asked = [request.path for request, _ in serverpartdeals.log]
    assert asked.count("/robots.txt") == 2


def test_a_request_that_is_not_a_source_is_refused(api: CollectorApi) -> None:
    missing = httpx.post(f"{api.url}/preview", json={"kind": "shopify"}, timeout=30)
    unreadable = httpx.post(f"{api.url}/preview", content=b"not json", timeout=30)
    elsewhere = httpx.post(f"{api.url}/nowhere", json={}, timeout=30)
    nothing_there = httpx.get(f"{api.url}/nowhere", timeout=30)

    assert (missing.status_code, missing.json()) == (422, {"detail": "missing base_url"})
    assert (unreadable.status_code, elsewhere.status_code) == (422, 404)
    assert nothing_there.status_code == 404


def test_a_store_that_answers_in_a_shape_the_reader_cannot_read_is_an_error_not_a_hang(
    api: CollectorApi, serverpartdeals: HTTPServer
) -> None:
    serve_robots(serverpartdeals)
    serverpartdeals.expect_request("/collections/hard-drives/products.json").respond_with_json(
        {"unexpected": []}
    )

    answer = api.preview(kind="shopify", base_url=base_of(serverpartdeals), settings=SHOPIFY)

    assert (answer.status_code, answer.json()) == (500, {"detail": "KeyError('products')"})
    assert api.stop()[-1]["event"] == "preview_crashed"


def test_a_preview_does_not_wait_behind_a_scheduled_run(
    disktracker: HTTPServer, goharddrive: HTTPServer, serverpartdeals: HTTPServer
) -> None:
    started, release = threading.Event(), threading.Event()

    def hang(_: Request) -> Response:
        # The scheduled run's store answers only once the preview is done.
        started.set()
        release.wait(timeout=30)
        return Response("User-agent: *\nDisallow:\n", content_type="text/plain")

    goharddrive.expect_request("/robots.txt").respond_with_handler(hang)
    serve_shop(serverpartdeals)
    scheduled = source_json("goharddrive", "sitemap", base_of(goharddrive), SITEMAP)
    running = start_api(disktracker, scheduled)
    assert started.wait(timeout=30), "the scheduled run never started"

    asked = time.monotonic()
    answer = running.preview(kind="shopify", base_url=base_of(serverpartdeals), settings=SHOPIFY)
    took = time.monotonic() - asked
    release.set()
    running.stop()

    assert answer.json()["status"] == "found"
    assert took < 10, took
