import json
import re
import subprocess
import time
from itertools import pairwise
from typing import Any

from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

from tests.builders import listing_json, sitemap_settings
from tests.integration.harness import (
    ALLOW_ALL,
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

FIXTURES = ROOT / "tests/fixtures/goharddrive"
AVOLUSION = "/Avolusion-PRO-5X-12TB-USB-3-0-HDD-PC-Mac-XBOX-p/g03-1842-xf.htm"
SEAGATE = "/DELL-Seagate-ST1000NM0023-1TB-7200RPM-SAS-HDD-p/g01-2130.htm"
HGST = "/Dell-HGST-HUS726T4TAL4205-4TB-12Gb-s-SAS-HDD-p/g01-2172-cr.htm"
MAXDIGITAL = "/MaxDigital-4TB-64MB-Cache-SATA3-3-5-Hard-Drive-p/g01-1060.htm"
PAGES = {
    AVOLUSION: "avolusion_drive.htm",
    SEAGATE: "maker_in_stock.htm",
    HGST: "hgst_refurbished_out_of_stock.htm",
    MAXDIGITAL: "maxdigital_own_brand.htm",
}
# In the sitemap but never worth fetching: not a drive, or not a product.
SKIPPED = [
    "/Avolusion-PRO-5X-USB-3-0-HDD-Enclosure-Grey-p/g04-0435.htm",
    "/ASUS-VE245H-Black-24-5ms-HDMI-Widescreen-TFT-LCD-p/g05-0001.htm",
    "/SSD-Solid-State-Drive-s/239.htm",
]


def page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="latin-1")


def serve_store(
    goharddrive: HTTPServer,
    paths: list[str],
    robots: str = ALLOW_ALL,
    failing: tuple[str, ...] = (),
    missing: tuple[str, ...] = (),
    requested_at: list[float] | None = None,
    pages: dict[str, str] | None = None,
    retitled: dict[str, tuple[str, str]] | None = None,
) -> None:
    """robots.txt, a sitemap listing these paths (plus ones never worth fetching), and each
    page, except that failing paths answer 503. requested_at collects when the sitemap and
    pages were asked for. pages adds paths answered with a fixture page; retitled adds paths
    answered with a fixture page under another title."""
    served = {**PAGES, **(pages or {})}
    titles = retitled or {}
    serve_robots(goharddrive, robots)
    base = base_of(goharddrive)
    entries = "".join(
        f"<url><loc>{base}{path}</loc><lastmod>2026-09-26</lastmod></url>"
        for path in [*paths, *SKIPPED]
    )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>'
    )

    def respond(request: Request) -> Response:
        if requested_at is not None:
            requested_at.append(time.monotonic())
        if request.path == "/sitemap.xml":
            return Response(sitemap, content_type="text/xml")
        if request.path in failing:
            return Response("busy", status=503)
        if request.path in missing:
            return Response("", status=404)
        if request.path in titles:
            fixture, title = titles[request.path]
            body = re.sub(
                r"<title>.*?</title>", f"<title>{title}</title>", page(fixture), flags=re.DOTALL
            )
            body = re.sub(r'og:title" content="[^"]*"', f'og:title" content="{title}"', body)
        else:
            body = page(served[request.path])
        return Response(body, content_type="text/html; charset=ISO-8859-1")

    for path in ["/sitemap.xml", *paths]:
        goharddrive.expect_request(path).respond_with_handler(respond)


def run_collector(
    goharddrive: HTTPServer, disktracker: HTTPServer
) -> subprocess.CompletedProcess[str]:
    return run(environment(disktracker, ghd_source(goharddrive)))


def ghd_source(goharddrive: HTTPServer) -> dict[str, Any]:
    """goHardDrive as the collector's sitemap source, configured as disktracker seeds it: the
    collector works out its titles, own brands and which pages name a capacity."""
    settings = sitemap_settings(
        product_path_pattern="-p/", free_shipping_marker="Help_FreeShipping"
    )
    return source_json("goharddrive", "sitemap", base_of(goharddrive), settings)


def offer(url: str, **fields: Any) -> dict[str, Any]:
    return {
        "source": "goharddrive",
        "seller": "",
        "url": url,
        "aliases": [],
        "brand": None,
        **fields,
    }


def test_one_run_posts_every_drive_in_the_sitemap_and_fetches_nothing_else(
    goharddrive: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_store(goharddrive, [AVOLUSION, SEAGATE, HGST, MAXDIGITAL])
    record_everything(disktracker)
    know_listings(disktracker, [], store="goharddrive")

    result = run_collector(goharddrive, disktracker)

    assert result.returncode == 0, result.stderr
    assert [request.path for request, _ in goharddrive.log] == [
        "/robots.txt",
        "/sitemap.xml",
        AVOLUSION,
        SEAGATE,
        HGST,
        MAXDIGITAL,
    ]
    posted = [json.loads(request.data) for request in posts(disktracker)]
    for posting in posted:
        posting.pop("observed_at")
    base = base_of(goharddrive)
    assert posted == [
        offer(
            f"{base}{AVOLUSION}",
            title="Avolusion PRO-5X (Grey) 12TB USB 3.0 External Hard Drive for PC, Mac, Xbox"
            " - 2 Year Warranty",
            mpn="G03-1842-XF",
            brand="Avolusion",
            condition="new",
            capacity_gb=12000,
            item_price_cents=29999,
            shipping_cents=0,
            in_stock=True,
            specifications={"media_type": "hdd", "interface": "usb"},
        ),
        offer(
            f"{base}{SEAGATE}",
            title="DELL / Seagate Constellation ES.3 ST1000NM0023 1TB 7200 RPM 128MB Cache SAS"
            " 6Gb/s 3.5 Inch Enterprise Internal Hard Drive - 5 Year Warranty",
            mpn="ST1000NM0023",
            brand="Seagate",
            condition="new",
            capacity_gb=1000,
            item_price_cents=3995,
            shipping_cents=0,
            in_stock=True,
            specifications={
                "media_type": "hdd",
                "form_factor": "3_5",
                "interface": "sas",
                "intended_use": ["enterprise"],
            },
        ),
        offer(
            f"{base}{HGST}",
            title="Dell / HGST Ultrastar DC HC300 HUS726T4TAL4205 4TB 7200RPM 256MB Cache SAS"
            " 12Gb/s 3.5 Inch Enterprise Hard Drive (Refurbished)- w/3 Year Warranty",
            mpn="HUS726T4TAL4205",
            brand="Western Digital",
            condition="refurbished",
            capacity_gb=4000,
            item_price_cents=7999,
            shipping_cents=None,
            in_stock=False,
            specifications={
                "media_type": "hdd",
                "form_factor": "3_5",
                "interface": "sas",
                "intended_use": ["enterprise"],
            },
        ),
        offer(
            f"{base}{MAXDIGITAL}",
            # As its og:title writes it.
            title="MaxDigital 4TB 7200RPM 64MB Cache SATA III 6.0Gb/s (Enterprise Storage) 3.5''"
            " Internal Hard Drive w/2 Year Warranty",
            mpn="G01-1060",
            brand="MaxDigital",
            condition="new",
            capacity_gb=4000,
            item_price_cents=11899,
            shipping_cents=0,
            in_stock=True,
            specifications={
                "media_type": "hdd",
                "form_factor": "3_5",
                "interface": "sata",
                "intended_use": ["enterprise"],
            },
        ),
    ]
    assert events(result.stdout)[-1] == {
        "event": "run_complete",
        "source": "goharddrive",
        "seen": 4,
        "recorded": 4,
        "queued": 0,
        "ignored": 0,
        "failed": 0,
        "rechecked": 0,
        "recheck_failed": 0,
        "stopped": False,
    }


def test_requests_wait_the_crawl_delay_robots_txt_asks_for(
    goharddrive: HTTPServer, disktracker: HTTPServer
) -> None:
    requested_at: list[float] = []
    serve_store(
        goharddrive,
        [SEAGATE, MAXDIGITAL],
        robots="User-agent: *\nCrawl-delay: 1\n",
        requested_at=requested_at,
    )
    record_everything(disktracker)
    know_listings(disktracker, [], store="goharddrive")

    result = run_collector(goharddrive, disktracker)

    assert result.returncode == 0, result.stderr
    assert len(requested_at) == 3
    gaps = [later - earlier for earlier, later in pairwise(requested_at)]
    assert min(gaps) >= 0.95, gaps


def test_offers_that_left_the_sitemap_are_rechecked_on_their_own_page(
    goharddrive: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_store(goharddrive, [SEAGATE])
    goharddrive.expect_request(HGST).respond_with_data(
        page(PAGES[HGST]), content_type="text/html; charset=ISO-8859-1"
    )
    gone = "/Discontinued-Drive-2TB-p/g01-0001.htm"
    goharddrive.expect_request(gone).respond_with_data("", status=404)
    base = base_of(goharddrive)
    known = {
        path: listing_json(
            f"{base}{path}",
            store="goharddrive",
            title=f"Known {path}",
            mpn=f"MPN{index}",
            condition="refurbished",
            capacity_gb=4000,
        )
        for index, path in enumerate([HGST, gone])
    }
    know_listings(disktracker, list(known.values()), store="goharddrive")
    record_everything(disktracker)

    result = run_collector(goharddrive, disktracker)

    assert result.returncode == 0, result.stderr
    reposted = rechecks(disktracker)
    for posting in reposted:
        posting.pop("observed_at")

    def repost(path: str, index: int, price: int | None) -> dict[str, Any]:
        return offer(
            f"{base}{path}",
            title=f"Known {path}",
            mpn=f"MPN{index}",
            condition="refurbished",
            capacity_gb=4000,
            item_price_cents=price,
            shipping_cents=None,
            in_stock=False,
            specifications=None,
        )

    assert reposted == [repost(HGST, 0, 7999), repost(gone, 1, None)]
    assert events(result.stdout)[-1]["rechecked"] == 2


def test_product_pages_that_fail_or_are_gone_are_reported_and_the_run_carries_on(
    goharddrive: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_store(goharddrive, [SEAGATE, HGST, MAXDIGITAL], failing=(SEAGATE,), missing=(HGST,))
    record_everything(disktracker)
    know_listings(disktracker, [], store="goharddrive")

    result = run_collector(goharddrive, disktracker)

    assert result.returncode == 0, result.stderr
    output = events(result.stdout)
    base = base_of(goharddrive)
    assert [event for event in output if event["event"] == "page_failed"] == [
        {
            "event": "page_failed",
            "source": "goharddrive",
            "url": f"{base}{SEAGATE}",
            "error": f"Server error '503 SERVICE UNAVAILABLE' for url '{base}{SEAGATE}'\n"
            "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503",
        },
        {
            "event": "page_failed",
            "source": "goharddrive",
            "url": f"{base}{HGST}",
            "error": f"Not found: {base}{HGST}",
        },
    ]
    assert [json.loads(request.data)["mpn"] for request in posts(disktracker)] == ["G01-1060"]
    assert (output[-1]["seen"], output[-1]["recorded"]) == (1, 1)


def test_a_run_announces_itself_and_posts_each_drive_as_soon_as_its_page_is_read(
    goharddrive: HTTPServer, disktracker: HTTPServer
) -> None:
    requested_at: list[float] = []
    serve_store(goharddrive, [SEAGATE, MAXDIGITAL], requested_at=requested_at)
    posted_at: list[float] = []

    def record(_request: Request) -> Response:
        posted_at.append(time.monotonic())
        return Response(
            json.dumps({"status": "recorded", "listing_id": None, "unmatched_id": None}),
            status=201,
            content_type="application/json",
        )

    disktracker.expect_request("/api/scraped", method="POST").respond_with_handler(record)
    know_listings(disktracker, [], store="goharddrive")

    result = run_collector(goharddrive, disktracker)

    assert result.returncode == 0, result.stderr
    assert events(result.stdout)[:2] == [
        {"event": "run_started", "source": "goharddrive"},
        {"event": "sitemap_read", "source": "goharddrive", "pages": 2},
    ]
    assert len(posted_at) == 2
    assert posted_at[0] < requested_at[-1], "the first drive is posted before the last page is read"


def test_drives_are_named_by_their_makers_mpn_so_they_match_other_stores(
    goharddrive: HTTPServer, disktracker: HTTPServer
) -> None:
    """A real brand's MPN is read from the title; a real brand without one waits for review
    instead of taking the store's code, whether disktracker knows the brand or not; only store
    brands and drives sold as white label, which no other store sells, are named by that code,
    the last part of their page's path."""
    western_digital = "/Western-Digital-RE-WD2000FYYZ-2TB-SATA3-Hard-Drive-p/g01-0101.htm"
    kingston = "/Kingston-240GB-SATA-III-2-5-SSD-p/g02-0202.htm"
    white_label = "/MDD-4TB-7200RPM-SATA-3-5-Hard-Drive-p/g01-0303.htm"
    unknown_maker = "/HPE-P42575-004-PM1653-7-68TB-SAS-12Gbps-SFF-SSD-p/g02-0404.htm"
    store_named = "/WL-150GB-10000RPM-SATA-3-5-Hard-Drive-p/g01-0644.htm"
    retitled = {
        western_digital: (PAGES[MAXDIGITAL], "Western Digital RE WD2000FYYZ 2TB SATA3 Hard Drive"),
        kingston: (PAGES[MAXDIGITAL], "Kingston 240GB SATA III 2.5 SSD"),
        white_label: (PAGES[MAXDIGITAL], "MDD 4TB 7200RPM 64MB Cache SATA 3.5 Hard Drive"),
        unknown_maker: (PAGES[MAXDIGITAL], "HPE P42575-004 PM1653 7.68TB SAS 12Gbps SFF SSD"),
        # As the store titles the pages of the drives it sells under no maker's name.
        store_named: (PAGES[MAXDIGITAL], "goHardDrive.com - WL 150GB 10000RPM SATA 3.5 Drive"),
    }
    serve_store(goharddrive, [*retitled, MAXDIGITAL], retitled=retitled)
    record_everything(disktracker)
    know_listings(disktracker, [], store="goharddrive")

    result = run_collector(goharddrive, disktracker)

    assert result.returncode == 0, result.stderr
    named = [
        (offer["title"].split()[0], offer["mpn"])
        for offer in (json.loads(request.data) for request in posts(disktracker))
    ]
    assert named == [
        ("Western", "WD2000FYYZ"),
        ("Kingston", None),
        ("MDD", "G01-0303"),
        ("HPE", None),
        ("goHardDrive.com", "G01-0644"),
        ("MaxDigital", "G01-1060"),
    ]


def test_the_sitemap_robots_txt_names_is_read_through_its_index(
    goharddrive: HTTPServer, disktracker: HTTPServer
) -> None:
    base = base_of(goharddrive)
    robots = f"User-agent: *\nDisallow:\nSitemap: {base}/sitemap-index.xml\n"
    serve_store(goharddrive, [SEAGATE], robots=robots)
    goharddrive.expect_request("/sitemap-index.xml").respond_with_data(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<sitemap><loc>{base}/sitemap.xml</loc></sitemap></sitemapindex>",
        content_type="text/xml",
    )
    record_everything(disktracker)
    know_listings(disktracker, [], store="goharddrive")

    result = run_collector(goharddrive, disktracker)

    assert result.returncode == 0, result.stderr
    assert [request.path for request, _ in goharddrive.log] == [
        "/robots.txt",
        "/sitemap-index.xml",
        "/sitemap.xml",
        SEAGATE,
    ]
    assert [json.loads(request.data)["mpn"] for request in posts(disktracker)] == ["ST1000NM0023"]


def test_a_sitemap_its_index_lists_twice_is_read_once(
    goharddrive: HTTPServer, disktracker: HTTPServer
) -> None:
    base = base_of(goharddrive)
    robots = f"User-agent: *\nDisallow:\nSitemap: {base}/sitemap-index.xml\n"
    serve_store(goharddrive, [SEAGATE], robots=robots)
    listed = f"<sitemap><loc>{base}/sitemap.xml</loc></sitemap>"
    goharddrive.expect_request("/sitemap-index.xml").respond_with_data(
        f"<sitemapindex>{listed}{listed}</sitemapindex>", content_type="text/xml"
    )
    record_everything(disktracker)
    know_listings(disktracker, [], store="goharddrive")

    result = run_collector(goharddrive, disktracker)

    assert result.returncode == 0, result.stderr
    assert [request.path for request, _ in goharddrive.log] == [
        "/robots.txt",
        "/sitemap-index.xml",
        "/sitemap.xml",
        SEAGATE,
    ]
    assert events(result.stdout)[-1]["seen"] == 1
