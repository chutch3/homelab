"""A listing is what one store page says one offer is, before anyone trusts it: its store, page,
seller, and the MPN and condition the page gives. Each is queued, decided, cleared and held on its
own, though several share a page."""

from typing import Any

from fastapi.testclient import TestClient
from test_api import post, scraped_payload

from disktracker.main import create_app

PAGE = "https://www.serverpartdeals.com/products/exos"


def listing(**fields: Any) -> dict[str, Any]:
    """An observation of the page, as the collector posts it."""
    return scraped_payload(url=PAGE, **fields)


def waiting(client: TestClient) -> list[tuple[str | None, str | None, str]]:
    return sorted(
        ((item["mpn"], item["condition"], item["reason"])
         for item in client.get("/api/review-items").json()),
        key=lambda item: tuple(value or "" for value in item),
    )  # fmt: skip


def match(client: TestClient, item: str, **decision: Any) -> Any:
    body = {"decision": "match", "mpn": "ST18000NM000J", "condition": "new", "capacity_gb": 18000}
    return client.put(f"/api/review-items/{item}/decision", json={**body, **decision})


def test_two_offers_of_one_page_wait_for_review_and_are_decided_each_on_its_own(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        new = post(client, "/api/prices", listing(mpn=None, condition="new")).json()
        used = post(client, "/api/prices", listing(mpn=None, condition="used")).json()
        both = waiting(client)
        decided = match(client, new["review_item_id"])
        left = waiting(client)

    assert both == [(None, "new", "missing_mpn"), (None, "used", "missing_mpn")]
    assert decided.status_code == 200, decided.text
    assert left == [(None, "used", "missing_mpn")]
    assert used["review_item_id"] != new["review_item_id"]


def test_a_decision_governs_only_the_listing_it_was_made_of(database_url: str) -> None:
    """Another product of the same page is no more decided than any other page's."""
    with TestClient(create_app()) as client:
        queued = post(client, "/api/prices", listing(mpn=None, condition="new")).json()
        match(client, queued["review_item_id"])
        again = post(
            client, "/api/prices", listing(mpn=None, condition="new", item_price_cents=35000)
        )
        sibling = post(client, "/api/prices", listing(mpn=None, condition="used"))

    assert again.json()["status"] == "recorded"
    assert sibling.json()["status"] == "queued"


def test_an_accepted_listing_is_trusted_as_it_was_seen_and_judged_again_once_it_reads_otherwise(
    database_url: str,
) -> None:
    """Accepted, its title read again is as accepted; a title that now reads as several drives is
    new evidence, and waits for a person again."""
    title = "Seagate Exos X18 18TB"
    with TestClient(create_app()) as client:
        queued = post(client, "/api/prices", listing(mpn=None, title=title)).json()
        match(client, queued["review_item_id"], condition="manufacturer_recertified")
        seen_again = post(
            client, "/api/prices", listing(mpn=None, title=title, item_price_cents=35000)
        )
        changed = post(
            client,
            "/api/prices",
            listing(mpn=None, title=f"{title} 4-pack", item_price_cents=34000),
        )

    assert seen_again.json()["status"] == "recorded"
    assert changed.json()["status"] == "queued"


def test_a_listing_recorded_clears_only_what_waits_of_that_very_listing(database_url: str) -> None:
    """Being on the same page and saying less is no evidence of being the same product: what
    waits of another listing of the page, one that gave no MPN, waits still."""
    with TestClient(create_app()) as client:
        post(client, "/api/prices", listing(mpn=None, condition="new"))
        post(
            client,
            "/api/prices",
            listing(mpn="ST18000NM000J", condition="new", title="Exos X18 18TB 4-pack"),
        )
        before = waiting(client)
        recorded = post(client, "/api/prices", listing(mpn="ST18000NM000J", condition="new"))
        after = waiting(client)

    assert before == [(None, "new", "missing_mpn"), ("ST18000NM000J", "new", "not_a_single_drive")]
    assert recorded.json()["status"] == "recorded"
    assert after == [(None, "new", "missing_mpn")]


def test_a_doubted_listing_holds_only_the_offer_it_is_of(database_url: str) -> None:
    with TestClient(create_app()) as client:
        new = post(client, "/api/prices", listing(condition="new")).json()["offer_id"]
        used = post(client, "/api/prices", listing(condition="used")).json()["offer_id"]
        post(client, "/api/prices", listing(condition="new", title="Exos X18 18TB 4-pack"))
        doubts = {o["id"]: o["doubt"] for o in client.get("/api/offers").json()}

    assert doubts == {new: "not_a_single_drive", used: None}


def test_what_a_queued_listing_said_of_its_drive_is_kept_for_review(database_url: str) -> None:
    specifications = {"interface": "sas", "recording_type": "cmr"}
    with TestClient(create_app()) as client:
        post(client, "/api/prices", listing(
            mpn=None, aliases=["0XYZ18"], brand="Seagate", specifications=specifications,
        ))  # fmt: skip
        [item] = client.get("/api/review-items").json()

    assert (item["aliases"], item["brand"]) == (["0XYZ18"], "Seagate")
    assert {k: item["specifications"][k] for k in specifications} == specifications
