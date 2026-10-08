"""With COLLECTOR_PROXY_URL set, everything the collector fetches from a store goes out through
that proxy (a VPN's, say), so the store sees the proxy's address and not the collector's; what
it says to disktracker does not. The proxy below forwards as an HTTP proxy does, and keeps what
it was asked for."""

import json
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

import httpx
import pytest
from pytest_httpserver import HTTPServer

from tests.integration.harness import (
    base_of,
    environment,
    events,
    know_listings,
    posts,
    record_everything,
    run,
    source_json,
)
from tests.integration.test_browser_transport_run import (
    PRODUCTS,
    browser_source,
    serve_browser,
    serve_store,
)

VIA = "X-Forwarded-By"


class ForwardingProxy:
    def __init__(self) -> None:
        self.asked: list[str] = []
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                # A proxy is asked for the whole URL.
                proxy.asked.append(self.path)
                agent = self.headers.get("User-Agent", "")
                fetched = httpx.get(self.path, headers={VIA: "proxy", "User-Agent": agent})
                self.send_response(fetched.status_code)
                self.send_header("Content-Type", fetched.headers.get("content-type", "text/plain"))
                self.send_header("Content-Length", str(len(fetched.content)))
                self.end_headers()
                self.wfile.write(fetched.content)

            def log_message(self, format: str, *args: Any) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def proxy() -> Iterator[ForwardingProxy]:
    forwarding = ForwardingProxy()
    yield forwarding
    forwarding.stop()


def direct_source(store: HTTPServer) -> dict[str, Any]:
    settings = {"collections": ["drives"], "free_shipping": False}
    return source_json("orbit", "shopify", base_of(store), settings)


def test_a_store_is_fetched_through_the_proxy_and_disktracker_is_not(
    serverpartdeals: HTTPServer, disktracker: HTTPServer, proxy: ForwardingProxy
) -> None:
    serve_store(serverpartdeals)
    know_listings(disktracker, [], store="orbit")
    record_everything(disktracker)

    result = run(
        environment(disktracker, direct_source(serverpartdeals), COLLECTOR_PROXY_URL=proxy.url)
    )

    assert result.returncode == 0, result.stderr
    # Every request the store saw came from the proxy, robots.txt included.
    assert {request.headers.get(VIA) for request, _ in serverpartdeals.log} == {"proxy"}
    base = base_of(serverpartdeals)
    assert proxy.asked[:2] == [f"{base}/robots.txt", f"{base}{PRODUCTS}?limit=250&page=1"]
    assert all(asked.startswith(base) for asked in proxy.asked)
    assert len(posts(disktracker)) == 3
    assert events(result.stdout)[-1]["recorded"] == 3


def test_a_proxy_that_cannot_be_reached_fails_the_run_rather_than_going_direct(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_store(serverpartdeals)
    record_everything(disktracker)

    result = run(
        environment(
            disktracker, direct_source(serverpartdeals), COLLECTOR_PROXY_URL="http://127.0.0.1:9"
        )
    )

    # A failed run, as for any store that cannot be reached.
    assert result.returncode == 1
    [failed] = [event for event in events(result.stdout) if event["event"] == "run_failed"]
    assert failed["error"].startswith("robots.txt: ")
    assert serverpartdeals.log == []
    assert posts(disktracker) == []


def test_a_browser_is_told_to_fetch_through_the_proxy_too(
    serverpartdeals: HTTPServer, disktracker: HTTPServer, flaresolverr: HTTPServer
) -> None:
    serve_store(serverpartdeals)
    know_listings(disktracker, [], store="orbit")
    record_everything(disktracker)
    browser = serve_browser(flaresolverr)

    result = run(
        environment(
            disktracker,
            browser_source(serverpartdeals),
            COLLECTOR_PROXY_URL="http://vpn:8888",
            **browser,
        )
    )

    assert result.returncode == 0, result.stderr
    asked = [json.loads(request.data) for request, _ in flaresolverr.log]
    assert asked and all(request["proxy"] == {"url": "http://vpn:8888"} for request in asked)
