"""A price of an offer whose drive is already known: named by the offer's id, or by its drive with
the store, seller and condition it is offered in. Recording it never establishes what a drive
is: a drive is made or corrected beforehand, and a page described is taken in at /ingestions."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_api import held_reasons, post, scraped_payload

from disktracker.main import create_app


def a_drive(client: TestClient, mpn: str = "ST18000NM000J", capacity_gb: int = 18000) -> str:
    made = client.post("/api/drives", json={"mpn": mpn, "capacity_gb": capacity_gb})
    assert made.status_code == 201, made.text
    drive_id: str = made.json()["id"]
    return drive_id


def entered(drive_id: str, **fields: Any) -> dict[str, Any]:
    """A price a person enters for a drive at a one-off store."""
    return {
        "drive_id": drive_id,
        "store": "other",
        "seller": "Example seller",
        "condition": "new",
        "item_price_cents": 18900,
        "observed_at": "2026-09-21T12:00:00Z",
        **fields,
    }


def test_a_price_for_a_drive_is_of_its_offer_at_that_store_from_that_seller_in_that_condition(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        drive_id = a_drive(client)
        first = post(
            client,
            "/api/prices",
            entered(drive_id, title="Exos X18", url="https://example.com/x18"),
        )
        again = post(
            client,
            "/api/prices",
            entered(drive_id, item_price_cents=17900, observed_at="2026-09-22T12:00:00Z"),
        )
        used = post(client, "/api/prices", entered(drive_id, condition="used"))
        untitled = post(client, "/api/prices", entered(drive_id, seller="Another seller"))
        offer = client.get(f"/api/offers/{first.json()['offer_id']}").json()
        named_by_mpn = client.get(f"/api/offers/{untitled.json()['offer_id']}").json()["title"]  # fmt: skip

    assert [r.status_code for r in (first, again, used, untitled)] == [201] * 4
    assert again.json()["offer_id"] == first.json()["offer_id"] != used.json()["offer_id"]
    assert (offer["drive"]["id"], offer["title"], offer["url"]) == (
        drive_id, "Exos X18", "https://example.com/x18",
    )  # fmt: skip
    assert [p["item_price_cents"] for p in offer["observations"]] == [18900, 17900]
    assert named_by_mpn == "ST18000NM000J"


def test_a_price_of_a_drive_or_store_not_known_is_refused(database_url: str) -> None:
    with TestClient(create_app()) as client:
        drive_id = a_drive(client)
        no_drive = post(client, "/api/prices", entered(str(uuid4())))
        no_store = post(client, "/api/prices", entered(drive_id, store="nowhere", seller=""))
        kept = client.get("/api/offers").json()

    assert no_drive.status_code == 404
    assert no_store.status_code == 422
    assert kept == []


@pytest.mark.parametrize(
    "fields",
    [
        {"drive_id": None},
        {"offer_id": "11111111-1111-4111-8111-111111111111"},
        {"mpn": "ST18000NM000J"},
        {"capacity_gb": 18000},
        {"brand": "Seagate"},
        {"specifications": {"interface": "sata"}},
        {"aliases": ["0XYZ"]},
        {"on_unmatched": "queue"},
    ],
    ids=["no drive", "drive and offer", "mpn", "capacity", "brand", "specifications", "aliases",
         "review policy"],
)  # fmt: skip
def test_a_price_says_nothing_of_what_its_drive_is(
    database_url: str, fields: dict[str, Any]
) -> None:
    """What establishes or describes a drive, or asks for review, is ingestion's."""
    with TestClient(create_app()) as client:
        drive_id = a_drive(client)
        refused = post(client, "/api/prices", {**entered(drive_id), **fields})
        kept = client.get("/api/offers").json()

    assert refused.status_code == 422, refused.text
    assert kept == []


def test_a_price_entered_for_a_drive_leaves_its_offer_held(database_url: str) -> None:
    """It says nothing new of what the page is."""
    page = scraped_payload(condition="new")
    with TestClient(create_app()) as client:
        clean = post(client, "/api/ingestions", page).json()
        bundle = "Seagate Exos X18 ST18000NM000J 18TB 4-pack"
        post(client, "/api/ingestions", {**page, "title": bundle, "observed_at": "2026-09-22T12:00:00Z"})  # fmt: skip
        drive_id = client.get(f"/api/offers/{clean['offer_id']}").json()["drive"]["id"]
        by_hand = post(client, "/api/prices", entered(
            drive_id, store="serverpartdeals", seller="", observed_at="2026-09-23T12:00:00Z",
        ))  # fmt: skip

    assert by_hand.json()["offer_id"] == clean["offer_id"]
    assert held_reasons(database_url) == {"new": "not_a_single_drive"}
