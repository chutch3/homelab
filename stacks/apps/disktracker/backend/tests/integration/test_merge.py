"""Merging one drive into another, the one way two drives become one: the target survives, with
every MPN the source went by, its offers and their prices; what both drives know and differ on
is refused, and nothing is changed."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import Response
from test_api import entered, post, price_payload, scraped_payload
from test_persistence import LOCK, crossing, meanwhile

from disktracker.main import create_app


def drive(client: TestClient, mpn: str, **fields: Any) -> dict[str, Any]:
    made = client.post("/api/drives", json={"mpn": mpn, "capacity_gb": 16000, **fields})
    assert made.status_code == 201, made.text
    found: dict[str, Any] = made.json()
    return found


def offer(client: TestClient, mpn: str, key: str | None = None, **fields: Any) -> str:
    recorded = post(
        client,
        "/api/prices",
        entered(client, price_payload(mpn=mpn, capacity_gb=16000, **fields)),
        key,
    )
    assert recorded.status_code == 201, recorded.text
    offer_id: str = recorded.json()["offer_id"]
    return offer_id


def merge(client: TestClient, source: str, target: str, key: str | None = None) -> Response:
    return client.post(
        f"/api/drives/{source}/merge",
        json={"target_drive_id": target},
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def test_a_drive_merged_into_another_gives_it_every_mpn_it_went_by_and_its_offers(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        target = drive(client, "WUH721816AL5205")
        source = drive(client, "0HNHWC")
        client.post(f"/api/drives/{source['id']}/aliases", json={"mpn": "0HNHWC-G14"})
        kept = offer(
            client, "WUH721816AL5205", store="goharddrive", seller="", condition="refurbished"
        )
        moved = offer(client, "0HNHWC", store="serverpartdeals", seller="", condition="new")
        merged = merge(client, source["id"], target["id"])
        after = client.get(f"/api/drives/{target['id']}").json()
        gone = client.get(f"/api/drives/{source['id']}")

    assert merged.status_code == 200, merged.text
    assert merged.json() == {
        "status": "merged", "drive_id": target["id"], "absorbed_drive_id": source["id"],
        "combined_offers": [],
    }  # fmt: skip
    assert sorted(after["drive"]["aliases"]) == ["0HNHWC", "0HNHWC-G14"]
    assert sorted(o["id"] for o in after["offers"]) == sorted([kept, moved])
    assert {o["mpn"] for o in after["offers"]} == {"WUH721816AL5205"}
    assert gone.status_code == 404


def test_offers_of_the_same_store_seller_and_condition_are_one_with_both_their_prices(
    database_url: str,
) -> None:
    """The target's offer survives with every price of both, held if either was, last checked
    when either was; its page is the one kept. What a save answered before is answered again
    unchanged, naming the offer as it was."""
    page = scraped_payload(store="serverpartdeals", seller="", condition="new", capacity_gb=16000)
    with TestClient(create_app()) as client:
        target = drive(client, "WUH721816AL5205")
        source = drive(client, "0HNHWC")
        survivor = post(client, "/api/ingestions", {**page, "mpn": "WUH721816AL5205", "url": "https://spd.test/wd",
                        "title": "WD 16TB", "item_price_cents": 17500, "observed_at": "2026-10-02T12:00:00Z"}).json()  # fmt: skip
        key = str(uuid4())
        dell = {**page, "mpn": "0HNHWC", "url": "https://spd.test/dell", "title": "Dell 16TB",
                "item_price_cents": 18000, "observed_at": "2026-10-01T12:00:00Z"}  # fmt: skip
        absorbed = post(client, "/api/ingestions", dell, key).json()
        # Its page then reads as several drives: held.
        post(
            client,
            "/api/ingestions",
            {**dell, "title": "Dell 16TB 4-pack", "observed_at": "2026-10-03T12:00:00Z"},
        )
        merged = merge(client, source["id"], target["id"])
        kept = client.get(f"/api/offers/{survivor['offer_id']}").json()
        again = post(client, "/api/ingestions", dell, key)
        gone = client.get(f"/api/offers/{absorbed['offer_id']}")

    assert merged.json()["combined_offers"] == [
        {"absorbed_offer_id": absorbed["offer_id"], "offer_id": survivor["offer_id"]}
    ]
    assert [p["item_price_cents"] for p in kept["observations"]] == [18000, 17500]
    assert (kept["doubt"], kept["url"], kept["last_checked_at"]) == (
        # Checked last when the target's offer was: the absorbed page's last reading was doubted,
        # and queued rather than counted as a check.
        "not_a_single_drive", "https://spd.test/wd", "2026-10-02T12:00:00Z",
    )  # fmt: skip
    assert (again.status_code, again.json()) == (201, absorbed)
    assert gone.status_code == 404


def test_drives_that_differ_on_what_both_know_are_not_merged_and_nothing_changes(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        target = drive(client, "ST16000NM001G", specifications={"interface": "sas"})
        source = drive(
            client, "ST16000NM000J", capacity_gb=18000, specifications={"interface": "sata"}
        )
        refused = merge(client, source["id"], target["id"])
        both = [client.get(f"/api/drives/{d['id']}").json()["drive"] for d in (target, source)]

    assert refused.status_code == 409
    assert (
        "capacity_gb" in refused.json()["detail"]
        and "specifications.interface" in refused.json()["detail"]
    )
    assert both == [target, source]


def test_the_targets_brand_stands_and_what_it_lacks_comes_from_the_source(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        target = drive(client, "ST16000NM001G", brand="Seagate")
        source = drive(
            client, "ST16000NM000J", brand="SEAGATE", specifications={"interface": "sas"}
        )
        merge(client, source["id"], target["id"])
        merged = client.get(f"/api/drives/{target['id']}").json()["drive"]

    assert (merged["brand"], merged["specifications"]["interface"]) == ("Seagate", "sas")


def test_a_merge_sent_again_is_answered_as_it_was_and_its_key_cannot_merge_another(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        target, source, other = (drive(client, mpn) for mpn in ("AAA1", "BBB1", "CCC1"))
        key = str(uuid4())
        first = merge(client, source["id"], target["id"], key)
        again = merge(client, source["id"], target["id"], key)
        reused = merge(client, other["id"], target["id"], key)
        keyless = client.post(
            f"/api/drives/{other['id']}/merge", json={"target_drive_id": target["id"]}
        )
        itself = merge(client, target["id"], target["id"])
        unknown = merge(client, str(uuid4()), target["id"])

    assert (first.status_code, again.status_code, again.json()) == (200, 200, first.json())
    assert reused.status_code == 409
    assert keyless.status_code == 422
    assert (itself.status_code, unknown.status_code) == (422, 404)


def test_what_was_found_to_be_the_absorbed_drive_waiting_for_review_is_the_target_after(
    database_url: str,
) -> None:
    """Its submitted evidence is left as it was."""
    with TestClient(create_app()) as client:
        target = drive(client, "AAA1")
        source = drive(client, "BBB1")
        client.post(f"/api/drives/{source['id']}/aliases", json={"mpn": "0XYZ"})
        post(client, "/api/ingestions", scraped_payload(url="https://spd.test/c", mpn="CCC1", title="Drive 16TB",
                                                    capacity_gb=16000, aliases=["0XYZ"]))  # fmt: skip
        merge(client, source["id"], target["id"])
        [item] = client.get("/api/review-items").json()

    assert (item["conflict_drive_id"], item["aliases"]) == (target["id"], ["0XYZ"])


def test_a_page_of_the_absorbed_mpn_is_of_the_target_after(database_url: str) -> None:
    with TestClient(create_app()) as client:
        target = drive(client, "AAA1")
        source = drive(client, "BBB1")
        merge(client, source["id"], target["id"])
        later = offer(client, "BBB1", seller="Shop")
        recorded = client.get(f"/api/offers/{later}").json()["drive"]["id"]

    assert recorded == target["id"]


def test_a_merge_is_refused_if_what_the_source_goes_by_changes_as_it_starts(
    database_url: str,
) -> None:
    """Another MPN given to the source the moment before the merge takes hold of what it goes by
    is not taken silently: nothing is merged."""
    with TestClient(create_app()) as client:
        target = drive(client, "AAA1")
        source = drive(client, "BBB1")
        with meanwhile(
            database_url, LOCK,
            "INSERT INTO mpn_aliases (alias, drive_id) VALUES ('BBB1-X', :source)", source=source["id"],
        ) as changed:  # fmt: skip
            refused = merge(client, source["id"], target["id"])
        both = [client.get(f"/api/drives/{d['id']}").status_code for d in (target, source)]

    assert changed
    assert refused.status_code == 409
    assert both == [200, 200]


def test_a_merge_and_a_review_decision_at_once_both_finish(database_url: str) -> None:
    """A page naming another MPN of the drive being merged waits for review as a conflict with
    it; the reviewer settles it as the drive it is merged into as the merge runs. Both want what
    the drive goes by, and the merge wants the waiting item too: whichever goes first, neither
    waits for the other forever, and the listing is of the drive that survives."""
    pauses = {
        # The merge, once it holds what both drives go by, as it reaches the review queue.
        "merge": lambda statement, locks: statement.startswith("UPDATE unmatched"),
        # The reviewer, once it has its decision, as it asks for the first MPN it touches.
        "review": lambda statement, locks: LOCK in statement and locks == 1,
    }
    roles = {"INSERT INTO save_receipts": "merge", "INSERT INTO review_decisions": "review"}

    def assign(statement: str, parameters: Any) -> str | None:
        return next((role for start, role in roles.items() if statement.startswith(start)), None)

    with TestClient(create_app()) as client:
        target = drive(client, "AAA1")
        source = drive(client, "BBB1")
        client.post(f"/api/drives/{source['id']}/aliases", json={"mpn": "0XYZ"})
        item = post(client, "/api/ingestions", scraped_payload(
            url="https://spd.test/c", mpn="CCC1", condition="new", title="Drive 16TB",
            capacity_gb=16000, aliases=["0XYZ"],
        )).json()["review_item_id"]  # fmt: skip
        decision = {"decision": "match", "drive_id": target["id"], "condition": "new"}
        with crossing(assign, pauses), ThreadPoolExecutor(max_workers=2) as executor:
            merging = executor.submit(merge, client, source["id"], target["id"])
            deciding = executor.submit(
                client.put, f"/api/review-items/{item}/decision", json=decision
            )
            results = [merging.result(), deciding.result()]
        merged = client.get(f"/api/drives/{target['id']}").json()
        decided = results[1].json()["offer_id"]

    assert [result.status_code for result in results] == [200, 200], [r.text for r in results]
    assert sorted(merged["drive"]["aliases"]) == ["0XYZ", "BBB1"]
    assert decided in [offer["id"] for offer in merged["offers"]]


def test_a_decision_naming_a_drive_merged_away_is_refused_and_its_item_still_waits(
    database_url: str,
) -> None:
    """A drive absorbed is gone: the reviewer chooses the drive it became."""
    with TestClient(create_app()) as client:
        target = drive(client, "AAA1")
        source = drive(client, "BBB1")
        item = post(client, "/api/ingestions", scraped_payload(
            url="https://spd.test/c", mpn=None, title="Drive 16TB", capacity_gb=16000,
        )).json()["review_item_id"]  # fmt: skip
        merge(client, source["id"], target["id"])
        refused = client.put(
            f"/api/review-items/{item}/decision",
            json={"decision": "match", "drive_id": source["id"], "condition": "new"},
        )
        waiting = [i["id"] for i in client.get("/api/review-items").json()]

    assert refused.status_code == 404
    assert waiting == [item]


def test_a_decision_on_a_drive_merged_away_as_it_waits_is_refused_and_its_item_still_waits(
    database_url: str,
) -> None:
    """The reviewer names the drive being merged away, and waits for what it goes by while the
    merge holds it: once the merge is done, the drive is gone."""
    pauses = {
        "merge": lambda statement, locks: statement.startswith("UPDATE unmatched"),
        "review": lambda statement, locks: LOCK in statement and locks == 1,
    }
    roles = {"INSERT INTO save_receipts": "merge", "INSERT INTO review_decisions": "review"}

    def assign(statement: str, parameters: Any) -> str | None:
        return next((role for start, role in roles.items() if statement.startswith(start)), None)

    with TestClient(create_app()) as client:
        target = drive(client, "AAA1")
        source = drive(client, "BBB1")
        item = post(client, "/api/ingestions", scraped_payload(
            url="https://spd.test/c", mpn=None, title="Drive 16TB", capacity_gb=16000,
        )).json()["review_item_id"]  # fmt: skip
        decision = {"decision": "match", "drive_id": source["id"], "condition": "new"}
        with crossing(assign, pauses), ThreadPoolExecutor(max_workers=2) as executor:
            merging = executor.submit(merge, client, source["id"], target["id"])
            deciding = executor.submit(
                client.put, f"/api/review-items/{item}/decision", json=decision
            )
            results = [merging.result(), deciding.result()]
        waiting = [i["id"] for i in client.get("/api/review-items").json()]

    assert [result.status_code for result in results] == [200, 404], [r.text for r in results]
    assert waiting == [item]


def test_what_a_reviewer_decided_a_page_was_is_the_target_once_merged(database_url: str) -> None:
    """A page decided to be the absorbed drive, read again after the merge, is recorded as the
    drive it became, without waiting for review again."""
    page = scraped_payload(
        url="https://spd.test/c", mpn=None, title="Drive 16TB", capacity_gb=16000
    )
    with TestClient(create_app()) as client:
        target = drive(client, "AAA1")
        source = drive(client, "BBB1")
        item = post(client, "/api/ingestions", page).json()["review_item_id"]
        client.put(
            f"/api/review-items/{item}/decision",
            json={"decision": "match", "drive_id": source["id"], "condition": "new"},
        )
        merge(client, source["id"], target["id"])
        later = post(client, "/api/ingestions", {**page, "observed_at": "2026-10-03T12:00:00Z"})
        recorded = client.get(f"/api/offers/{later.json()['offer_id']}").json()["drive"]["id"]

    assert later.status_code == 201, later.text
    assert recorded == target["id"]
