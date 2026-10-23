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
from test_api import entered

from disktracker.main import create_app


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
def collector(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeCollector]:
    """The collector the application asks."""
    fake = FakeCollector()
    monkeypatch.setenv("DISKTRACKER_COLLECTOR_URL", fake.url)
    yield fake
    fake.stop()


def test_a_source_is_read_by_the_collector_as_it_would_be_saved_and_nothing_is_kept(
    database_url: str, collector: FakeCollector
) -> None:
    collector.finds()
    with TestClient(create_app()) as client:
        rules = client.get("/api/condition-rules").json()
        before = [source["key"] for source in client.get("/api/sources").json()]
        previewed = client.post("/api/source-previews", json={**SOURCE, "transport": "browser"})
        after = [source["key"] for source in client.get("/api/sources").json()]
        listings = client.get("/api/offers").json()

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
            "obey_robots": True,
            "settings": {"collections": ["hard-drives"], "free_shipping": False},
            "conditions": rules,
            # No one page was asked for: the collector reads what the store lists.
            "page_url": None,
        }
    ]
    assert (after, listings) == (before, [])


def test_a_source_permitted_to_ignore_robots_txt_is_tried_as_it_would_run(
    database_url: str, collector: FakeCollector
) -> None:
    collector.finds()
    permitted = {**SOURCE, "basis": "permission", "obey_robots": False}
    with TestClient(create_app()) as client:
        obeying = client.post("/api/source-previews", json=SOURCE)
        ignoring = client.post("/api/source-previews", json=permitted)

    assert (obeying.status_code, ignoring.status_code) == (200, 200), ignoring.text
    assert [asked["obey_robots"] for asked in collector.asked] == [True, False]


def test_the_verdict_weighs_the_offer_against_the_drive_disktracker_knows(
    database_url: str, collector: FakeCollector
) -> None:
    """Every verdict is the catalog rules' (tests/unit/catalog/test_rules.py); this is the one
    that needs the drive as disktracker has it."""
    collector.finds(
        **{**OFFER, "capacity_gb": 20000, "title": "Seagate Exos X18 ST18000NM000J 20TB"}
    )
    with TestClient(create_app()) as client:
        # ST18000NM000J is a drive disktracker already knows, at 18 TB.
        client.post(
            "/api/prices",
            json=entered(client, {"mpn": "ST18000NM000J", "store": "other", "seller": "Shop", "condition": "new",
                  "title": "Exos X18", "capacity_gb": 18000, "item_price_cents": 30000}),
            headers={"Idempotency-Key": str(uuid4())},
        )  # fmt: skip
        previewed = client.post("/api/source-previews", json=SOURCE)

    assert previewed.json()["verdict"] == {"outcome": "review", "reason": "capacity_conflict"}


def test_a_preview_without_an_offer_is_passed_on_as_the_collector_gave_it(
    database_url: str, collector: FakeCollector
) -> None:
    """Without an offer there is no verdict (tests/unit/collector/test_preview_service.py)."""
    collector.answer = {
        "status": "nothing",
        "reason": None,
        "offer": None,
        "notes": ["The sitemap lists 3 pages; 0 are product pages to read."],
    }
    with TestClient(create_app()) as client:
        previewed = client.post("/api/source-previews", json=SOURCE)

    assert previewed.json() == {**collector.answer, "verdict": None}


SITEMAP_SOURCE = {"name": "Seagate", "kind": "sitemap", "base_url": "https://www.seagate.com"}
PAGE = "https://www.seagate.com/products/nas-drives/ironwolf-pro-hard-drive/"


def test_a_sitemap_source_can_be_tested_on_one_of_its_pages(
    database_url: str, collector: FakeCollector
) -> None:
    with TestClient(create_app()) as client:
        previewed = client.post("/api/source-previews", json={**SITEMAP_SOURCE, "page_url": PAGE})

    assert previewed.status_code == 200, previewed.text
    assert [asked["page_url"] for asked in collector.asked] == [PAGE]


def test_a_source_that_could_not_be_saved_is_refused_before_the_collector_is_asked(
    database_url: str, collector: FakeCollector
) -> None:
    with TestClient(create_app()) as client:
        refused = client.post("/api/source-previews", json={**SOURCE, "settings": {}})

    assert refused.status_code == 422
    assert refused.json()["detail"][0]["loc"] == ["body", "settings", "collections"]
    assert collector.asked == []


def test_without_a_collector_to_ask_a_source_cannot_be_tested(
    collector: FakeCollector, monkeypatch: pytest.MonkeyPatch
) -> None:
    collector.status, collector.answer = 500, {"detail": "KeyError('products')"}
    with TestClient(create_app()) as client:
        crashed = client.post("/api/source-previews", json=SOURCE)
    monkeypatch.setenv("DISKTRACKER_COLLECTOR_URL", "http://127.0.0.1:9")
    with TestClient(create_app()) as client:
        unreachable = client.post("/api/source-previews", json=SOURCE)
    monkeypatch.delenv("DISKTRACKER_COLLECTOR_URL")
    with TestClient(create_app()) as client:
        unset = client.post("/api/source-previews", json=SOURCE)

    assert [answer.status_code for answer in (unset, unreachable, crashed)] == [503, 503, 503]
    assert unset.json() == {"detail": "No collector is configured, so sources cannot be tested."}
    assert unreachable.json()["detail"].startswith("The collector could not be reached")
    assert crashed.json() == {"detail": "The collector failed to read it: KeyError('products')"}


# A store disktracker collects, so its pages can be taken in before one is previewed.
SPD = {**SOURCE, "name": "ServerPartDeals", "base_url": "https://www.serverpartdeals.com"}
PAGE_AS_COLLECTED = {
    "store": "serverpartdeals", "seller": "", "url": OFFER["url"], "title": OFFER["title"],
    "mpn": OFFER["mpn"], "condition": OFFER["condition"], "capacity_gb": OFFER["capacity_gb"],
    "item_price_cents": OFFER["item_price_cents"], "shipping_cents": 0,
    "observed_at": "2026-10-01T12:00:00Z",
}  # fmt: skip


def ingest(client: TestClient, **fields: Any) -> dict[str, Any]:
    taken = client.post(
        "/api/ingestions",
        json={**PAGE_AS_COLLECTED, **fields},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert taken.status_code in (200, 201, 202), taken.text
    answer: dict[str, Any] = taken.json()
    return answer


def test_a_page_a_reviewer_said_is_nothing_to_track_previews_as_ignored(
    database_url: str, collector: FakeCollector
) -> None:
    """As ingestion follows what a reviewer decided of a listing, so does a preview of it."""
    bundle = f"{OFFER['title']} 4-pack"
    collector.finds(title=bundle, seller="")
    with TestClient(create_app()) as client:
        queued = ingest(client, title=bundle)
        client.put(
            f"/api/review-items/{queued['review_item_id']}/decision", json={"decision": "ignore"}
        )
        previewed = client.post("/api/source-previews", json=SPD)

    assert previewed.json()["verdict"] == {"outcome": "ignored", "reason": "decided"}


def test_a_sold_out_page_of_an_offer_with_a_price_previews_as_recorded(
    database_url: str, collector: FakeCollector
) -> None:
    """Sold out, it is recorded at the price it last had; only one never priced is ignored."""
    collector.finds(in_stock=False, item_price_cents=None, seller="")
    with TestClient(create_app()) as client:
        never_priced = client.post("/api/source-previews", json=SPD).json()["verdict"]
        ingest(client)
        priced = client.post("/api/source-previews", json=SPD).json()["verdict"]

    assert never_priced == {"outcome": "ignored", "reason": "sold_out"}
    assert priced == {"outcome": "recorded", "reason": None}


def test_a_page_naming_another_drives_mpn_previews_as_waiting_for_review(
    database_url: str, collector: FakeCollector
) -> None:
    """As ingestion queues it whole: no drive is merged for it."""
    collector.finds(aliases=["0HNHWC"], seller="")
    with TestClient(create_app()) as client:
        client.post("/api/drives", json={"mpn": "0HNHWC", "capacity_gb": 18000})
        previewed = client.post("/api/source-previews", json=SPD)

    assert previewed.json()["verdict"] == {"outcome": "review", "reason": "alias_conflict"}
