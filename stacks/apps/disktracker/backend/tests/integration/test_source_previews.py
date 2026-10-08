"""Testing a source before it is saved: the backend checks it as a save would, asks the
collector to read one offer from it, and says what disktracker would do with that offer.
Nothing is kept. The collector here is a fake that answers as the test scripts it."""

import json
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from disktracker.web import create_app


class FakeCollector:
    """Answers POST /preview with what the test set, and keeps what it was asked."""

    def __init__(self) -> None:
        self.status, self.answer = 200, {"status": "nothing", "reason": None, "offer": None}
        self.asked: list[dict[str, Any]] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                fake.asked.append(
                    {
                        "path": self.path,
                        **json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
                    }
                )
                content = json.dumps(fake.answer).encode()
                self.send_response(fake.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            def log_message(self, format: str, *args: Any) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        Thread(target=self.server.serve_forever, daemon=True).start()

    def finds(self, **offer: Any) -> None:
        self.answer = {"status": "found", "reason": None, "offer": {**OFFER, **offer}}

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


OFFER = {
    "source": "serverorbit",
    "url": "https://www.serverorbit.com/products/exos-x18",
    "title": "Seagate Exos X18 ST18000NM000J 18TB",
    "mpn": "ST18000NM000J",
    "condition": "manufacturer_recertified",
    "capacity_gb": 18000,
    "item_price_cents": 36999,
    "in_stock": True,
    "seller": "",
    "shipping_cents": 0,
    "aliases": [],
    "specifications": {"media_type": "hdd"},
    "brand": "Seagate",
}
SOURCE = {
    "name": "Server Orbit",
    "kind": "shopify",
    "base_url": "https://www.serverorbit.com",
    "settings": {"collections": ["hard-drives"]},
}


@pytest.fixture
def collector() -> Iterator[FakeCollector]:
    fake = FakeCollector()
    yield fake
    fake.stop()


def test_a_source_is_read_by_the_collector_as_it_would_be_saved_and_nothing_is_kept(
    database_url: str, collector: FakeCollector
) -> None:
    collector.finds()
    with TestClient(create_app(database_url, collector.url)) as client:
        rules = client.get("/api/condition-rules").json()
        before = [source["key"] for source in client.get("/api/sources").json()]
        previewed = client.post("/api/source-previews", json={**SOURCE, "transport": "browser"})
        after = [source["key"] for source in client.get("/api/sources").json()]
        listings = client.get("/api/listings").json()

    assert previewed.status_code == 200, previewed.text
    assert previewed.json() == {
        "status": "found",
        "reason": None,
        "offer": {
            name: OFFER[name]
            for name in ("url", "title", "mpn", "brand", "condition", "capacity_gb",
                         "item_price_cents", "shipping_cents", "in_stock", "aliases")
        },
        "verdict": {"outcome": "recorded", "reason": None},
        "notes": [],
    }  # fmt: skip
    # The collector is given the source under the key it would have, with its settings' defaults
    # filled in and the condition rules as they are now.
    assert collector.asked == [
        {
            "path": "/preview",
            "key": "serverorbit",
            "kind": "shopify",
            "base_url": "https://www.serverorbit.com",
            "transport": "browser",
            "settings": {"collections": ["hard-drives"], "free_shipping": False},
            "conditions": rules,
            # No one page was asked for: the collector reads what the store lists.
            "page_url": None,
        }
    ]
    assert (after, listings) == (before, [])


@pytest.mark.parametrize(
    ("offer", "verdict"),
    [
        ({"mpn": None}, {"outcome": "review", "reason": "missing_mpn"}),
        ({"condition": None}, {"outcome": "review", "reason": "missing_condition"}),
        ({"capacity_gb": None}, {"outcome": "review", "reason": "missing_capacity"}),
        ({"capacity_gb": 20000}, {"outcome": "review", "reason": "capacity_conflict"}),
        ({"in_stock": False}, {"outcome": "ignored", "reason": "sold_out"}),
        ({"mpn": "ST20000NM007D", "capacity_gb": 20000}, {"outcome": "recorded", "reason": None}),
        ({}, {"outcome": "recorded", "reason": None}),
    ],
    ids=[
        "no MPN",
        "no condition",
        "no capacity for a new drive",
        "another capacity than the drive has",
        "sold out",
        "a new drive with its capacity",
        "a known drive at its capacity",
    ],
)
def test_the_verdict_says_what_disktracker_would_do_with_the_offer(
    database_url: str, collector: FakeCollector, offer: dict[str, Any], verdict: dict[str, Any]
) -> None:
    known = {**OFFER, "mpn": "WD181KFGX"} if offer.get("capacity_gb", 1) is None else OFFER
    collector.finds(**{**known, **offer})
    with TestClient(create_app(database_url, collector.url)) as client:
        # ST18000NM000J is a drive disktracker already knows, at 18 TB.
        client.post(
            "/api/prices",
            json={"mpn": "ST18000NM000J", "store": "other", "seller": "Shop", "condition": "new",
                  "title": "Exos X18", "capacity_gb": 18000, "item_price_cents": 30000},
            headers={"Idempotency-Key": str(uuid4())},
        )  # fmt: skip
        previewed = client.post("/api/source-previews", json=SOURCE)

    assert previewed.json()["verdict"] == verdict


@pytest.mark.parametrize(
    "answer",
    [
        {
            "status": "nothing",
            "reason": None,
            "offer": None,
            "notes": ["The sitemap lists 3 pages; 0 are product pages to read."],
        },
        {
            "status": "failed",
            "reason": "robots.txt disallows /collections/",
            "offer": None,
            "notes": [],
        },
    ],
    ids=["no drive found", "could not be read"],
)
def test_a_preview_without_an_offer_has_no_verdict(
    database_url: str, collector: FakeCollector, answer: dict[str, Any]
) -> None:
    collector.answer = answer
    with TestClient(create_app(database_url, collector.url)) as client:
        previewed = client.post("/api/source-previews", json=SOURCE)

    assert previewed.json() == {**answer, "verdict": None}


SITEMAP_SOURCE = {"name": "Seagate", "kind": "sitemap", "base_url": "https://www.seagate.com"}
PAGE = "https://www.seagate.com/products/nas-drives/ironwolf-pro-hard-drive/"


def test_a_sitemap_source_can_be_tested_on_one_of_its_pages(
    database_url: str, collector: FakeCollector
) -> None:
    with TestClient(create_app(database_url, collector.url)) as client:
        previewed = client.post("/api/source-previews", json={**SITEMAP_SOURCE, "page_url": PAGE})

    assert previewed.status_code == 200, previewed.text
    assert [asked["page_url"] for asked in collector.asked] == [PAGE]


@pytest.mark.parametrize(
    ("source", "complaint"),
    [
        ({**SOURCE, "page_url": PAGE}, "This kind of store cannot be tested on one page."),
        ({**SITEMAP_SOURCE, "page_url": "ironwolf-pro"}, "Enter the page's address"),
    ],
    ids=["a kind that reads no pages", "not an address"],
)
def test_a_page_that_cannot_be_tested_is_refused_on_the_page(
    database_url: str, collector: FakeCollector, source: dict[str, Any], complaint: str
) -> None:
    with TestClient(create_app(database_url, collector.url)) as client:
        refused = client.post("/api/source-previews", json=source)

    assert refused.status_code == 422
    [issue] = refused.json()["detail"]
    assert issue["loc"] == ["body", "page_url"]
    assert complaint in issue["msg"]
    assert collector.asked == []


def test_a_source_that_could_not_be_saved_is_refused_before_the_collector_is_asked(
    database_url: str, collector: FakeCollector
) -> None:
    with TestClient(create_app(database_url, collector.url)) as client:
        refused = client.post("/api/source-previews", json={**SOURCE, "settings": {}})

    assert refused.status_code == 422
    assert refused.json()["detail"][0]["loc"] == ["body", "settings", "collections"]
    assert collector.asked == []


def test_without_a_collector_to_ask_a_source_cannot_be_tested(
    database_url: str, collector: FakeCollector
) -> None:
    collector.status, collector.answer = 500, {"detail": "KeyError('products')"}
    with TestClient(create_app(database_url)) as client:
        unset = client.post("/api/source-previews", json=SOURCE)
    with TestClient(create_app(database_url, "http://127.0.0.1:9")) as client:
        unreachable = client.post("/api/source-previews", json=SOURCE)
    with TestClient(create_app(database_url, collector.url)) as client:
        crashed = client.post("/api/source-previews", json=SOURCE)

    assert [answer.status_code for answer in (unset, unreachable, crashed)] == [503, 503, 503]
    assert unset.json() == {"detail": "No collector is configured, so sources cannot be tested."}
    assert unreachable.json()["detail"].startswith("The collector could not be reached")
    assert crashed.json() == {"detail": "The collector failed to read it: KeyError('products')"}
