"""A source whose transport is browser is read through FlareSolverr: the fake below fetches
each page the way the real one does, as a browser, and answers as FlareSolverr's API does,
with a JSON document rendered as Chrome shows it."""

import html
import json
from typing import Any

import httpx
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

PAGE = json.loads((ROOT / "tests/fixtures/serverpartdeals_page1.json").read_text())
PRODUCTS = "/collections/drives/products.json"
VIA = "X-Fetched-By"


def browser_source(store: HTTPServer) -> dict[str, Any]:
    return source_json(
        "orbit",
        "shopify",
        base_of(store),
        {"collections": ["drives"], "free_shipping": False},
        transport="browser",
    )


def serve_store(store: HTTPServer) -> None:
    serve_robots(store)
    store.expect_request(PRODUCTS, query_string="limit=250&page=1").respond_with_json(
        {"products": PAGE["products"]}
    )
    store.expect_request(PRODUCTS, query_string="limit=250&page=2").respond_with_json(
        {"products": []}
    )


def as_chrome_shows(response: httpx.Response) -> str:
    if response.headers.get("content-type", "").startswith("application/json"):
        return (
            '<html><head><meta name="color-scheme" content="light dark"></head><body>'
            f'<pre style="word-wrap: break-word; white-space: pre-wrap;">{html.escape(response.text)}'
            "</pre></body></html>"
        )
    return response.text


def browse(request: Request) -> Response:
    asked = json.loads(request.data)
    assert (asked["cmd"], asked["maxTimeout"]) == ("request.get", 60000)
    fetched = httpx.get(asked["url"], headers={VIA: "flaresolverr"})
    solution = {
        "url": asked["url"],
        "status": fetched.status_code,
        "headers": dict(fetched.headers),
        "response": as_chrome_shows(fetched),
        "cookies": [],
        "userAgent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0",
    }
    answer = {"status": "ok", "message": "Challenge not detected!", "solution": solution}
    return Response(json.dumps(answer), content_type="application/json")


def serve_browser(flaresolverr: HTTPServer) -> dict[str, str]:
    flaresolverr.expect_request("/v1", method="POST").respond_with_handler(browse)
    return {"FLARESOLVERR_URL": base_of(flaresolverr)}


def test_a_browser_source_is_read_and_rechecked_through_flaresolverr_only(
    serverpartdeals: HTTPServer, disktracker: HTTPServer, flaresolverr: HTTPServer
) -> None:
    serve_store(serverpartdeals)
    gone = f"{base_of(serverpartdeals)}/products/gone"
    serverpartdeals.expect_request("/products/gone.js").respond_with_data("", status=404)
    know_listings(disktracker, [listing_json(gone, store="orbit")], store="orbit")
    record_everything(disktracker)
    browser = serve_browser(flaresolverr)

    result = run(environment(disktracker, browser_source(serverpartdeals), **browser))

    assert result.returncode == 0, result.stderr
    assert {request.headers.get(VIA) for request, _ in serverpartdeals.log} == {"flaresolverr"}
    assert [request.path for request, _ in serverpartdeals.log][:2] == ["/robots.txt", PRODUCTS]
    posted = [json.loads(request.data) for request in posts(disktracker)][:3]
    # The source is the store: its offers name it once, by its key.
    assert [(offer["source"], offer["mpn"]) for offer in posted] == [
        ("orbit", "ST18000NM003D"),
        ("orbit", "WUH721818ALE6L4"),
        ("orbit", None),
    ]
    assert all("store" not in offer and "retailer" not in offer for offer in posted)
    [recheck] = rechecks(disktracker)
    assert (recheck["url"], recheck["item_price_cents"], recheck["in_stock"]) == (
        gone,
        None,
        False,
    )


def test_a_page_flaresolverr_cannot_get_fails_the_run_with_its_reason(
    serverpartdeals: HTTPServer, disktracker: HTTPServer, flaresolverr: HTTPServer
) -> None:
    flaresolverr.expect_request("/v1", method="POST").respond_with_json(
        {"status": "error", "message": "Error solving the challenge. Timeout after 60.0 seconds."},
        status=500,
    )

    result = run(
        environment(
            disktracker,
            browser_source(serverpartdeals),
            FLARESOLVERR_URL=base_of(flaresolverr),
        )
    )

    assert result.returncode == 1
    assert serverpartdeals.log == []
    [failed] = [event for event in events(result.stdout) if event["event"] == "run_failed"]
    assert failed["error"] == (
        "robots.txt: browser: Error solving the challenge. Timeout after 60.0 seconds."
    )


def test_a_browser_source_without_flaresolverr_fails_its_run(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    result = run(environment(disktracker, browser_source(serverpartdeals)))

    assert result.returncode == 1
    assert serverpartdeals.log == []
    [failed] = [event for event in events(result.stdout) if event["event"] == "run_failed"]
    assert (failed["source"], failed["error"]) == (
        "orbit",
        "settings: fetching through a browser needs FLARESOLVERR_URL",
    )
