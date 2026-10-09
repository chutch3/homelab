import json
import time
from itertools import pairwise
from typing import Any

from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

from tests.builders import listing_json
from tests.integration.harness import (
    ROOT,
    base_of,
    environment,
    events,
    know_listings,
    posts,
    rechecks,
    record_everything,
    run,
    serve_robots,
    source_json,
)

FIXTURES = ROOT / "tests/fixtures/westerndigital"
API = "/wdwebservices/v2/us/products"
RED = "/products/internal-drives/wd-red-plus-sata-3-5-hdd?sku=WD120EFBX"
ULTRASTAR = "/products/internal-drives/data-center-drives/ultrastar-dc-hc550-hdd?sku=0F38352"
RECERTIFIED = (
    "/products/recertified/internal-drives/data-center-drives/"
    "ultrastar-dc-hc520-hdd-recertified?sku=R0F29590"
)
# A product WD lists but does not sell: no price.
UNPRICED = "/products/internal-drives/ultrastar-dc-hc650-hdd?sku=ULTRASTAR-DC-HC650-20-TB"
# In the sitemap but not internal drives.
SKIPPED = [
    "/products/external-drives/my-book-usb-3-0-hdd?sku=WDBBGB0040HBK-NESN",
    "/products/data-center-platforms/ultrastar-data60-platform?sku=DATA60-ONE-PT-EIGHT-PB",
]


def product(sku: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((FIXTURES / f"{sku}.json").read_text())
    return loaded


def serve_store(
    store: HTTPServer,
    paths: list[str],
    failing: tuple[str, ...] = (),
    requested_at: list[float] | None = None,
) -> None:
    """robots.txt, a sitemap listing these product pages (and ones that are not internal
    drives), and the product API answering for each fixture SKU; failing SKUs answer 503."""
    serve_robots(store)
    base = base_of(store)
    entries = "".join(f"<url><loc>{base}{path}</loc></url>" for path in [*SKIPPED, *paths])
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>'
    )

    def respond(request: Request) -> Response:
        if requested_at is not None:
            requested_at.append(time.monotonic())
        if request.path == "/products-sitemap.xml":
            return Response(sitemap, content_type="text/xml")
        sku = request.path.rsplit("/", 1)[1]
        if sku in failing:
            return Response("busy", status=503)
        return Response(json.dumps(product(sku)), content_type="application/json")

    store.expect_request("/products-sitemap.xml").respond_with_handler(respond)
    for sku in ("WD120EFBX", "0F38352", "R0F29590", "ULTRASTAR-DC-HC650-20-TB"):
        store.expect_request(f"{API}/{sku}").respond_with_handler(respond)


def wd_source(store: HTTPServer) -> dict[str, Any]:
    """Western Digital as the collector's SAP Commerce source, configured as disktracker seeds it."""
    settings = {
        "api_url": f"{base_of(store)}/wdwebservices/v2", "site": "us",
        "sitemap_path": "/products-sitemap.xml",
        "product_path_pattern": "^/products/(recertified/)?internal-drives/",
        "recertified_sku_prefix": "R",
    }  # fmt: skip
    return source_json("westerndigital", "sap_commerce", base_of(store), settings)


def run_collector(store: HTTPServer, disktracker: HTTPServer, delay: str = "0") -> Any:
    return run(environment(disktracker, wd_source(store), COLLECTOR_MIN_DELAY_SECONDS=delay))


def offer(url: str, **fields: Any) -> dict[str, Any]:
    return {
        "source": "westerndigital",
        "seller": "",
        "url": url,
        "shipping_cents": None,
        "aliases": [],
        "brand": None,
        **fields,
    }


def test_one_run_posts_every_internal_drive_on_sale_new_ones_before_recertified(
    westerndigital: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_store(westerndigital, [RECERTIFIED, RED, UNPRICED, ULTRASTAR])
    record_everything(disktracker)
    know_listings(disktracker, [], store="westerndigital")

    result = run_collector(westerndigital, disktracker)

    assert result.returncode == 0, result.stderr
    assert [request.path for request, _ in westerndigital.log] == [
        "/robots.txt",
        "/products-sitemap.xml",
        f"{API}/WD120EFBX",
        f"{API}/ULTRASTAR-DC-HC650-20-TB",
        f"{API}/0F38352",
        f"{API}/R0F29590",
    ]
    posted = [json.loads(request.data) for request in posts(disktracker)]
    for posting in posted:
        posting.pop("observed_at")
    base = base_of(westerndigital)
    assert posted == [
        offer(
            f"{base}{RED}",
            title="WD Red™ Plus - 12TB",
            mpn="WD120EFBX",
            brand="Western Digital",
            condition="new",
            capacity_gb=12000,
            item_price_cents=56499,
            in_stock=False,
            specifications={"media_type": "hdd", "intended_use": ["nas"]},
        ),
        # The model number is what other stores sell it under; WD's part number joins it.
        offer(
            f"{base}{ULTRASTAR}",
            title="Ultrastar® DC HC550 - 18TB",
            mpn="WUH721818AL5201",
            brand="Western Digital",
            aliases=["0F38352"],
            condition="new",
            capacity_gb=18000,
            item_price_cents=98499,
            in_stock=True,
            specifications={
                "media_type": "hdd",
                "interface": "sas",
                "intended_use": ["enterprise"],
            },
        ),
        # A recertified drive is known only by its part number, which a new one taught.
        offer(
            f"{base}{RECERTIFIED}",
            title="Ultrastar® DC HC520 - 12TB",
            mpn="0F29590",
            brand="Western Digital",
            condition="manufacturer_recertified",
            capacity_gb=12000,
            item_price_cents=65499,
            in_stock=True,
            specifications={
                "media_type": "hdd",
                "interface": "sata",
                "intended_use": ["enterprise"],
            },
        ),
    ]
    assert events(result.stdout)[-1] == {
        "event": "run_complete",
        "source": "westerndigital",
        "seen": 3,
        "recorded": 3,
        "queued": 0,
        "ignored": 0,
        "failed": 0,
        "rechecked": 0,
        "recheck_failed": 0,
        "stopped": False,
    }


def test_requests_are_spaced_even_though_the_site_asks_for_no_crawl_delay(
    westerndigital: HTTPServer, disktracker: HTTPServer
) -> None:
    requested_at: list[float] = []
    serve_store(westerndigital, [RED, ULTRASTAR], requested_at=requested_at)
    record_everything(disktracker)
    know_listings(disktracker, [], store="westerndigital")

    result = run_collector(westerndigital, disktracker, delay="0.5")

    assert result.returncode == 0, result.stderr
    assert len(requested_at) == 3
    gaps = [later - earlier for earlier, later in pairwise(requested_at)]
    assert min(gaps) >= 0.45, gaps


def test_a_product_the_api_fails_on_is_reported_and_the_run_carries_on(
    westerndigital: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_store(westerndigital, [RED, ULTRASTAR], failing=("WD120EFBX",))
    record_everything(disktracker)
    know_listings(disktracker, [], store="westerndigital")

    result = run_collector(westerndigital, disktracker)

    assert result.returncode == 0, result.stderr
    output = events(result.stdout)
    failed = [event for event in output if event["event"] == "page_failed"]
    assert [(event["source"], event["url"]) for event in failed] == [
        ("westerndigital", f"{base_of(westerndigital)}{API}/WD120EFBX")
    ]
    assert [json.loads(request.data)["mpn"] for request in posts(disktracker)] == [
        "WUH721818AL5201"
    ]


def test_offers_that_left_the_sitemap_are_rechecked_through_the_api(
    westerndigital: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_store(westerndigital, [RED])
    gone = "/products/internal-drives/wd-gold-sata-hdd?sku=WD2005FBYZ"
    westerndigital.expect_request(f"{API}/WD2005FBYZ").respond_with_data("", status=404)
    base = base_of(westerndigital)
    known = [
        listing_json(
            f"{base}{path}",
            store="westerndigital",
            title=f"Known {mpn}",
            mpn=mpn,
            condition="manufacturer_recertified",
            capacity_gb=12000,
        )
        for path, mpn in [(RECERTIFIED, "0F29590"), (gone, "WD2005FBYZ")]
    ]
    know_listings(disktracker, known, store="westerndigital")
    record_everything(disktracker)

    result = run_collector(westerndigital, disktracker)

    assert result.returncode == 0, result.stderr
    reposted = rechecks(disktracker)
    for posting in reposted:
        posting.pop("observed_at")

    def repost(path: str, mpn: str, price: int | None, in_stock: bool) -> dict[str, Any]:
        return offer(
            f"{base}{path}",
            title=f"Known {mpn}",
            mpn=mpn,
            condition="manufacturer_recertified",
            capacity_gb=12000,
            item_price_cents=price,
            in_stock=in_stock,
            specifications=None,
        )

    assert reposted == [
        repost(RECERTIFIED, "0F29590", 65499, True),
        repost(gone, "WD2005FBYZ", None, False),
    ]
    assert events(result.stdout)[-1]["rechecked"] == 2
