"""Inspecting a link to a store disktracker does not read yet: the backend asks the collector
which kind of source would read the page and with what settings, and says what recording the
offer those settings read would do. Nothing is kept. The collector here is the fake the source
preview tests use."""

from typing import Any

from fastapi.testclient import TestClient
from test_source_previews import OFFER, FakeCollector, collector  # noqa: F401

from disktracker.web import create_app

PAGE = "https://www.seagate.com/products/nas-drives/ironwolf-pro-hard-drive/"
SETTINGS = {"sitemap_path": "/sitemap.xml", "product_path_pattern": "^/products/"}
CANDIDATE = {
    "kind": "sitemap",
    "settings": SETTINGS,
    "evidence": ["The page carries its products as data in one of its scripts."],
    "offers": 8,
    "offer": {**OFFER, "url": PAGE, "mpn": None},
    # How much there is to the store, for deciding whether it is worth collecting.
    "summary": [
        {"label": "Pages a run would fetch", "value": "145"},
        {"label": "Time for a run", "value": "about 49 minutes (146 requests, 20 seconds apart)"},
    ],
}
INSPECTED = {
    "status": "found",
    "reason": None,
    "base_url": "https://www.seagate.com",
    "candidates": [CANDIDATE],
    "notes": ["No price was found in the page's markup or JSON-LD."],
}


def test_a_link_is_inspected_by_the_collector_and_each_way_of_reading_it_gets_a_verdict(
    database_url: str,
    collector: FakeCollector,  # noqa: F811
) -> None:
    collector.answer = INSPECTED
    with TestClient(create_app(database_url, collector.url)) as client:
        rules = client.get("/api/condition-rules").json()
        inspected = client.post(
            "/api/source-inspections", json={"url": PAGE, "transport": "browser"}
        )
        sources = client.get("/api/sources").json()

    assert inspected.status_code == 200, inspected.text
    shown = {name: OFFER[name] for name in ("title", "brand", "condition", "capacity_gb",
                                            "item_price_cents", "shipping_cents", "in_stock",
                                            "aliases")}  # fmt: skip
    assert inspected.json() == {
        **INSPECTED,
        "candidates": [
            {
                **CANDIDATE,
                "offer": {**shown, "url": PAGE, "mpn": None},
                "verdict": {"outcome": "review", "reason": "missing_mpn"},
            }
        ],
    }
    assert collector.asked == [
        {"path": "/inspect", "url": PAGE, "transport": "browser", "conditions": rules}
    ]
    # Nothing was added: only the stores disktracker is seeded with are there.
    assert "seagate" not in [source["key"] for source in sources]


def test_a_link_that_reads_as_nothing_or_cannot_be_read_is_passed_on_as_it_is(
    database_url: str,
    collector: FakeCollector,  # noqa: F811
) -> None:
    failed: dict[str, Any] = {
        "status": "failed",
        "reason": "Client error '403 FORBIDDEN'",
        "base_url": "https://www.seagate.com",
        "candidates": [],
        "notes": [],
    }
    collector.answer = failed
    with TestClient(create_app(database_url, collector.url)) as client:
        inspected = client.post("/api/source-inspections", json={"url": PAGE})

    assert inspected.json() == failed
    assert collector.asked[0]["transport"] == "direct"


def test_what_is_not_a_link_is_refused_before_the_collector_is_asked(
    database_url: str,
    collector: FakeCollector,  # noqa: F811
) -> None:
    with TestClient(create_app(database_url, collector.url)) as client:
        refused = client.post("/api/source-inspections", json={"url": "seagate ironwolf"})
        no_collector = TestClient(create_app(database_url)).post(
            "/api/source-inspections", json={"url": PAGE}
        )

    assert refused.status_code == 422
    assert refused.json()["detail"][0]["loc"] == ["body", "url"]
    assert collector.asked == []
    assert no_collector.status_code == 503
