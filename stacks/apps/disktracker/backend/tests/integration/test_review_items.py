"""The review queue: what waits in it, and what a reviewer's decision on an item does."""

from typing import Any
from uuid import uuid4

from api_calls import entered, match, post, price_payload, scraped_payload
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from disktracker.main import create_app


def test_the_review_queue_can_be_read_a_part_at_a_time_by_store_and_reason(
    subject: TestClient,
) -> None:
    """So whatever works through a long queue, a person or a program, can take it in batches."""
    for number, (source, mpn, condition) in enumerate(
        [
            ("serverpartdeals", None, "new"),
            ("goharddrive", None, "new"),
            ("goharddrive", "ST18000NM000J", None),
            ("goharddrive", None, "new"),
        ]
    ):
        queued = subject.post(
            "/api/ingestions",
            json=scraped_payload(
                store=source,
                mpn=mpn,
                condition=condition,
                url=f"https://store.test/drive-{number}",
                observed_at=f"2026-09-21T12:0{number}:00Z",
            ),
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert queued.status_code == 202, queued.text

    def queue(**query: Any) -> tuple[list[str], str]:
        answer = subject.get("/api/review-items", params=query)
        assert answer.status_code == 200, answer.text
        return [item["url"][-1] for item in answer.json()], answer.headers["X-Total-Count"]

    # Newest first, as before; the header counts what the filters match, not the page.
    assert queue() == (["3", "2", "1", "0"], "4")
    assert queue(store="goharddrive") == (["3", "2", "1"], "3")
    assert queue(store="goharddrive", reason="missing_mpn") == (["3", "1"], "2")
    assert queue(reason="missing_condition") == (["2"], "1")
    assert queue(limit=2) == (["3", "2"], "4")
    assert queue(limit=2, offset=2) == (["1", "0"], "4")
    assert queue(store="goharddrive", limit=1, offset=2) == (["1"], "3")
    refused = [
        subject.get("/api/review-items", params=query).status_code
        for query in ({"limit": 0}, {"limit": 501}, {"offset": -1}, {"reason": "bored"})
    ]
    assert refused == [422, 422, 422, 422]


def test_a_capacity_conflict_is_shown_with_the_drive_and_settled_either_way(
    subject: TestClient,
) -> None:
    """A reviewer sees the drive an offer's MPN names beside what was collected, and says which
    capacity is right: the drive's, so the offer is recorded as that drive; or the offer's, so
    the drive is corrected first (PATCH /drives/{id}), for every offer of it, and the offer then
    recorded as that drive. A decision never says what a drive is."""
    base = "https://www.serverorbit.com/products/"
    mpn = "P09094-H21"
    # Recorded long ago with a capacity misread from its title.
    stored = post(
        subject, "/api/prices", entered(subject, price_payload(mpn=mpn, capacity_gb=213200))
    )
    conflicts = [
        post(subject, "/api/ingestions", scraped_payload(url=base + name, mpn=mpn,
             title=f"HPE {mpn} 3.2TB SAS", capacity_gb=3200, condition="refurbished",
             seller=name)).json()["review_item_id"]
        for name in ("kept", "corrected")
    ]  # fmt: skip
    unnamed = post(subject, "/api/ingestions", scraped_payload(url=base + "unnamed", mpn=None))
    queue = {item["id"]: item for item in subject.get("/api/review-items").json()}
    drive_id = queue[conflicts[0]]["drive"]["id"]

    def decide(item: str) -> Any:
        body = {"decision": "match", "drive_id": drive_id, "condition": "refurbished"}
        return subject.put(f"/api/review-items/{item}/decision", json=body)

    kept = decide(conflicts[0])
    drive_kept = subject.get(f"/api/offers/{kept.json()['offer_id']}").json()["drive"]
    subject.patch(f"/api/drives/{drive_id}", json={"capacity_gb": 3200})
    corrected = decide(conflicts[1])
    first = subject.get(f"/api/offers/{stored.json()['offer_id']}").json()

    assert queue[conflicts[0]]["drive"]["mpn"] == mpn
    assert queue[conflicts[0]]["drive"]["capacity_gb"] == 213200
    assert queue[unnamed.json()["review_item_id"]]["drive"] is None
    assert kept.status_code == 200, kept.text
    assert drive_kept["capacity_gb"] == 213200
    assert corrected.status_code == 200, corrected.text
    # Corrected for every offer of the drive, the one recorded long ago too.
    assert (first["drive"]["capacity_gb"], first["capacity_gb"]) == (3200, 3200)


def test_resolving_a_queued_offer_records_it_and_later_scrapes_match_directly(
    subject: TestClient,
) -> None:
    url = "https://www.serverpartdeals.com/products/mystery"
    queued = post(subject, "/api/ingestions", scraped_payload(mpn=None, condition=None, url=url))
    item_id = queued.json()["review_item_id"]
    resolved = subject.put(
        f"/api/review-items/{item_id}/decision",
        json=match(subject, "ST18000NM000J", "manufacturer_recertified", 18000),
    )
    assert resolved.status_code == 200, resolved.text
    offer = subject.get(f"/api/offers/{resolved.json()['offer_id']}").json()
    assert (offer["mpn"], offer["latest"]["item_price_cents"]) == ("ST18000NM000J", 36999)
    assert offer["latest"]["provenance"] == "collected"
    assert subject.get("/api/review-items").json() == []
    later = post(
        subject,
        "/api/ingestions",
        scraped_payload(
            mpn=None,
            condition=None,
            url=url,
            item_price_cents=34999,
            observed_at="2026-09-22T12:00:00Z",
        ),
    )
    assert later.status_code == 201, later.text
    assert later.json()["offer_id"] == offer["id"]
    saved = subject.get(f"/api/offers/{offer['id']}").json()
    assert [o["item_price_cents"] for o in saved["observations"]] == [36999, 34999]
    missing = subject.put(
        f"/api/review-items/{uuid4()}/decision", json=match(subject, "X", "new", 1000)
    )
    assert missing.status_code == 404


def test_ignoring_a_queued_offer_keeps_later_scrapes_of_it_out_of_the_queue(
    subject: TestClient,
) -> None:
    url = "https://www.serverpartdeals.com/products/not-a-drive"
    queued = post(subject, "/api/ingestions", scraped_payload(mpn=None, url=url)).json()
    ignored = subject.put(
        f"/api/review-items/{queued['review_item_id']}/decision", json={"decision": "ignore"}
    )
    assert ignored.status_code == 200, ignored.text
    assert subject.get("/api/review-items").json() == []
    later = post(subject, "/api/ingestions", scraped_payload(mpn=None, url=url))
    assert later.status_code == 200
    assert later.json() == {
        "status": "ignored",
        "offer_id": None,
        "price_id": None,
        "review_item_id": None,
    }
    assert subject.get("/api/review-items").json() == []
    assert subject.get("/api/offers").json() == []


def a_match(client: TestClient) -> dict[str, Any]:
    return match(client, "ST18000NM000J", "manufacturer_recertified", 18000)


def queued_item(client: TestClient, **fields: Any) -> str:
    queued = post(client, "/api/ingestions", scraped_payload(mpn=None, condition=None, **fields))
    assert queued.status_code == 202, queued.text
    item_id: str = queued.json()["review_item_id"]
    return item_id


def test_a_review_decision_is_answered_again_when_repeated_without_doing_it_twice(
    subject: TestClient,
) -> None:
    """A decision whose answer was lost can be sent again: the same decision gets the first answer
    and records nothing more, while a different one is refused."""
    item_id = queued_item(subject)
    decided = subject.put(f"/api/review-items/{item_id}/decision", json=a_match(subject))
    waiting = subject.get("/api/review-items").json()
    repeated = subject.put(f"/api/review-items/{item_id}/decision", json=a_match(subject))
    changed = subject.put(f"/api/review-items/{item_id}/decision", json={"decision": "ignore"})
    offer = subject.get(f"/api/offers/{decided.json()['offer_id']}").json()
    assert decided.status_code == 200, decided.text
    assert decided.json() == {"status": "matched", "offer_id": offer["id"]}
    assert waiting == []
    assert (repeated.status_code, repeated.json()) == (200, decided.json())
    assert changed.status_code == 409, changed.text
    assert [price["item_price_cents"] for price in offer["observations"]] == [36999]
    assert (offer["mpn"], offer["condition"]) == ("ST18000NM000J", "manufacturer_recertified")


def test_an_ignore_decision_names_no_offer_and_is_answered_again_when_repeated(
    subject: TestClient,
) -> None:
    item_id = queued_item(subject)
    ignored = subject.put(f"/api/review-items/{item_id}/decision", json={"decision": "ignore"})
    repeated = subject.put(f"/api/review-items/{item_id}/decision", json={"decision": "ignore"})
    changed = subject.put(f"/api/review-items/{item_id}/decision", json=a_match(subject))
    offers = subject.get("/api/offers").json()
    assert (ignored.status_code, ignored.json()) == (200, {"status": "ignored", "offer_id": None})
    assert (repeated.status_code, repeated.json()) == (200, ignored.json())
    assert changed.status_code == 409, changed.text
    assert offers == []


def test_a_review_decision_must_say_what_it_decides_and_nothing_else(subject: TestClient) -> None:
    item_id = queued_item(subject)
    # What a decision may say is the schema's (tests/unit/catalog/test_schemas.py).
    unclear = subject.put(f"/api/review-items/{item_id}/decision", json={"decision": "keep"})
    unknown = subject.put(f"/api/review-items/{uuid4()}/decision", json=a_match(subject))
    still_waiting = [item["id"] for item in subject.get("/api/review-items").json()]
    assert unclear.status_code == 422
    assert [issue["loc"] for issue in unclear.json()["detail"]] == [["body", "decision"]]
    assert unknown.status_code == 404, unknown.text
    assert still_waiting == [item_id]


def test_a_review_decision_that_fails_partway_leaves_no_decision_and_can_be_made_again(
    database_url: str,
) -> None:
    """A decision is kept with what it changed, or not at all."""
    engine = create_engine(database_url)
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        item_id = queued_item(client)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE FUNCTION refuse() RETURNS trigger AS $$ BEGIN"
                    " RAISE EXCEPTION 'refused'; END $$ LANGUAGE plpgsql;"
                    " CREATE TRIGGER refuse BEFORE INSERT ON scraped_matches"
                    " FOR EACH ROW EXECUTE FUNCTION refuse();"
                )
            )
        failed = client.put(f"/api/review-items/{item_id}/decision", json=a_match(client))
        offers = client.get("/api/offers").json()
        with engine.begin() as connection:
            connection.execute(text("DROP TRIGGER refuse ON scraped_matches"))
        retried = client.put(f"/api/review-items/{item_id}/decision", json=a_match(client))
    engine.dispose()
    assert (failed.status_code, offers) == (500, [])
    assert (retried.status_code, retried.json()["status"]) == (200, "matched")


def test_the_review_queue_names_the_store_each_offer_was_seen_at(subject: TestClient) -> None:
    queued_item(subject)
    queued_item(subject, store="goharddrive", url="https://www.goharddrive.com/p/1")
    everything = subject.get("/api/review-items").json()
    one_store = subject.get("/api/review-items", params={"store": "goharddrive"})
    assert {item["store"] for item in everything} == {"serverpartdeals", "goharddrive"}
    assert [item["store"] for item in one_store.json()] == ["goharddrive"]
    assert one_store.headers["X-Total-Count"] == "1"


def test_a_decision_on_an_item_that_is_not_waiting_is_not_found_whatever_it_decides(
    subject: TestClient,
) -> None:
    ignored = subject.put(f"/api/review-items/{uuid4()}/decision", json={"decision": "ignore"})
    matched = subject.put(
        f"/api/review-items/{uuid4()}/decision", json=match(subject, "X", "new", 1000)
    )
    no_drive = subject.put(
        f"/api/review-items/{queued_item(subject)}/decision",
        json={"decision": "match", "drive_id": str(uuid4()), "condition": "new"},
    )
    still = [item["id"] for item in subject.get("/api/review-items").json()]

    assert [ignored.status_code, matched.status_code, no_drive.status_code] == [404, 404, 404]
    # Refused for a drive not known, the item still waits.
    assert len(still) == 1
