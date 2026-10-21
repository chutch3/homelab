"""Taking in a page as collected: one request per observation, answered with one outcome, its
save key answering it again as it was. A price of an offer already known, a recheck among them,
is not ingested: it gives no new evidence of what the page is."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_api import post, scraped_payload

from disktracker.main import create_app


def test_a_collected_page_is_taken_in_once_whatever_times_it_is_sent(database_url: str) -> None:
    with TestClient(create_app()) as client:
        key = str(uuid4())
        first = post(client, "/api/ingestions", scraped_payload(), key)
        again = post(client, "/api/ingestions", scraped_payload(), key)
        queued = post(
            client, "/api/ingestions", scraped_payload(mpn=None, url="https://spd.test/x")
        )
        prices = client.get("/api/prices", params={"offer_id": first.json()["offer_id"]}).json()

    assert (first.status_code, first.json()["status"]) == (201, "recorded")
    assert (again.status_code, again.json()) == (201, first.json())
    assert (queued.status_code, queued.json()["status"]) == (202, "queued")
    assert prices["total"] == 1


@pytest.mark.parametrize(
    "fields",
    [
        {"offer_id": "11111111-1111-4111-8111-111111111111"},
        {"provenance": "collected"},
        {"on_unmatched": "queue"},
        {"url": None},
        {"title": None},
    ],
    ids=["named offer", "provenance", "review policy", "no page", "no title"],
)
def test_only_a_page_as_collected_is_taken_in(database_url: str, fields: dict[str, Any]) -> None:
    """Every page taken in is collected, and waits for review when it cannot be matched, which
    needs the page and title a reviewer is shown."""
    with TestClient(create_app()) as client:
        refused = post(client, "/api/ingestions", {**scraped_payload(), **fields})
        kept = client.get("/api/offers").json()

    assert refused.status_code == 422, refused.text
    assert kept == []


def test_a_collected_observation_of_a_described_offer_is_not_a_price(database_url: str) -> None:
    with TestClient(create_app()) as client:
        refused = post(client, "/api/prices", {**scraped_payload(), "provenance": "collected"})

    assert refused.status_code == 422
    assert "/api/ingestions" in refused.text
