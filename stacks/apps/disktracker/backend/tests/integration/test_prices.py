"""A price of an offer whose drive is already known: named by the offer's id, or by its drive with
the store, seller and condition it is offered in. Recording it never establishes what a drive
is: a drive is made or corrected beforehand, and a page described is taken in at /ingestions."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from api_calls import (
    collected_payload,
    entered,
    held_reasons,
    post,
    price_payload,
    saved_offer,
    scraped_payload,
    with_history,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from disktracker.main import create_app


def a_drive(client: TestClient, mpn: str = "ST18000NM000J", capacity_gb: int = 18000) -> str:
    made = client.post("/api/drives", json={"mpn": mpn, "capacity_gb": capacity_gb})
    assert made.status_code == 201, made.text
    drive_id: str = made.json()["id"]
    return drive_id


def priced_entry(drive_id: str, **fields: Any) -> dict[str, Any]:
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
            priced_entry(drive_id, title="Exos X18", url="https://example.com/x18"),
        )
        again = post(
            client,
            "/api/prices",
            priced_entry(drive_id, item_price_cents=17900, observed_at="2026-09-22T12:00:00Z"),
        )
        used = post(client, "/api/prices", priced_entry(drive_id, condition="used"))
        untitled = post(client, "/api/prices", priced_entry(drive_id, seller="Another seller"))
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
        no_drive = post(client, "/api/prices", priced_entry(str(uuid4())))
        no_store = post(client, "/api/prices", priced_entry(drive_id, store="nowhere", seller=""))
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
        refused = post(client, "/api/prices", {**priced_entry(drive_id), **fields})
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
        by_hand = post(client, "/api/prices", priced_entry(
            drive_id, store="serverpartdeals", seller="", observed_at="2026-09-23T12:00:00Z",
        ))  # fmt: skip

    assert by_hand.json()["offer_id"] == clean["offer_id"]
    assert held_reasons(database_url) == {"new": "not_a_single_drive"}


def test_offers_are_identified_by_store_and_optional_marketplace_seller(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        direct = post(
            client,
            "/api/prices",
            entered(client, price_payload(store="serverpartdeals", seller="")),
        )
        assert direct.status_code == 201, direct.text
        direct_offer = saved_offer(client, direct)
        assert (direct_offer["store"], direct_offer["seller"]) == ("serverpartdeals", "")
        again = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                entered(
                    client,
                    price_payload(
                        store="serverpartdeals", seller="  ", observed_at="2026-09-22T12:00:00Z"
                    ),
                ),
            ),
        )
        assert again["id"] == direct_offer["id"]
        beach_audio = saved_offer(
            client,
            post(client, "/api/prices", entered(client, price_payload(seller="Beach Audio"))),
        )
        drivedeals = saved_offer(
            client, post(client, "/api/prices", entered(client, price_payload(seller="drivedeals")))
        )
        assert len({direct_offer["id"], beach_audio["id"], drivedeals["id"]}) == 3
        assert (
            post(client, "/api/prices", entered(client, price_payload(store="frys"))).status_code
            == 422
        )
        assert (
            post(client, "/api/prices", entered(client, price_payload(store="newegg"))).status_code
            == 422
        )
        unnamed = post(
            client, "/api/prices", entered(client, price_payload(store="other", seller=""))
        )
        assert unnamed.status_code == 422
        assert unnamed.json()["detail"][0]["loc"] == ["body", "seller"]
        named = post(
            client,
            "/api/prices",
            entered(client, price_payload(store="other", seller="Local shop")),
        )
        assert named.status_code == 201, named.text


def test_offer_and_later_price_survive_a_new_application_instance(database_url: str) -> None:
    with TestClient(create_app()) as client:
        started = datetime.now(UTC)
        result = post(client, "/api/prices", entered(client, price_payload()))
        offer = saved_offer(client, result)
        assert str(UUID(offer["id"])) == offer["id"]
        assert offer["title"] == "Seagate Exos X18"
        assert offer["capacity_gb"] == 18000
        assert offer["latest"]["total_cents"] == 19900
        assert offer["latest"]["price_per_tb"] == "11.06"
        initial = offer["observations"][0]
        assert initial["observed_at"] == "2026-09-21T12:00:00Z"
        assert initial["provenance"] == "manual"
        assert started <= datetime.fromisoformat(initial["entered_at"]) <= datetime.now(UTC)
        later = post(
            client,
            "/api/prices",
            entered(
                client, price_payload(item_price_cents=17900, observed_at="2026-09-22T12:00:00Z")
            ),
        )
        assert later.status_code == 201, later.text

    with TestClient(create_app()) as restarted:
        saved = restarted.get(f"/api/offers/{offer['id']}").json()
        assert saved["latest"]["total_cents"] == 18900
        assert [o["item_price_cents"] for o in saved["observations"]] == [18900, 17900]
        assert saved["observations"][0] == initial
        assert with_history(restarted) == [saved]


def test_offers_carry_no_correction_archive_or_revision_state(database_url: str) -> None:
    with TestClient(create_app()) as client:
        offer = saved_offer(client, post(client, "/api/prices", entered(client, price_payload())))
        assert not {"corrections", "revision", "archived_at", "duplicate_of"} & set(offer)
        assert not {"corrections", "revision"} & set(offer["drive"])
        listing, observation = offer["id"], offer["latest"]["id"]
        assert post(client, "/api/offers", {}).status_code == 405
        for path in [
            f"/api/offers/{listing}/observations",
            f"/api/offers/{listing}/corrections",
            f"/api/offers/{listing}/observations/{observation}/corrections",
            f"/api/offers/{listing}/archive",
            f"/api/drives/{offer['drive']['id']}/corrections",
        ]:
            assert post(client, path, {}).status_code == 404, path


def test_retries_replay_the_original_result_and_reject_changed_payload(database_url: str) -> None:
    key = str(uuid4())
    with TestClient(create_app()) as client:
        first = post(client, "/api/prices", entered(client, price_payload()), key)
        retry = post(client, "/api/prices", entered(client, price_payload()), key)
        assert retry.status_code == 201
        assert retry.json() == first.json()
        assert len(with_history(client)[0]["observations"]) == 1
        changed = post(
            client, "/api/prices", entered(client, price_payload(item_price_cents=1)), key
        )
        assert changed.status_code == 409


def test_concurrent_retries_record_one_price(database_url: str) -> None:
    key = str(uuid4())
    with TestClient(create_app()) as client:

        def submit() -> dict[str, Any]:
            response = post(client, "/api/prices", entered(client, price_payload()), key)
            assert response.status_code == 201
            return response.json()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first, second = list(executor.map(lambda _: submit(), range(2)))
        assert first == second
        assert len(with_history(client)[0]["observations"]) == 1


def test_backdated_prices_preserve_the_latest_observation(database_url: str) -> None:
    with TestClient(create_app()) as client:
        post(client, "/api/prices", entered(client, price_payload()))
        older = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                entered(
                    client,
                    price_payload(item_price_cents=10000, observed_at="2026-09-20T12:00:00Z"),
                ),
            ),
        )
        assert older["latest"]["item_price_cents"] == 18900
        assert [o["item_price_cents"] for o in older["observations"]] == [10000, 18900]


def test_a_price_corrected_for_the_moment_it_was_seen_is_the_latest_everywhere(
    database_url: str,
) -> None:
    """Mistyped, then entered again for the same moment: the one entered last is the offer's
    price, as it is shown and as a later check is compared with."""
    with TestClient(create_app()) as client:
        post(client, "/api/prices", entered(client, price_payload(item_price_cents=18900)))
        corrected = saved_offer(
            client,
            post(client, "/api/prices", entered(client, price_payload(item_price_cents=17900))),
        )
        again = post(client, "/api/prices", entered(client, price_payload(item_price_cents=17900)))

    assert corrected["latest"]["item_price_cents"] == 17900
    assert [o["item_price_cents"] for o in corrected["observations"]] == [18900, 17900]
    # The correction seen again is only a check of it.
    assert (again.status_code, again.json()["price_id"]) == (201, None)


def test_a_price_left_without_shipping_or_time_is_free_and_seen_now(database_url: str) -> None:
    with TestClient(create_app()) as client:
        started = datetime.now(UTC)
        minimal = price_payload()
        for field in ("shipping_cents", "observed_at", "notes"):
            del minimal[field]
        saved = post(client, "/api/prices", entered(client, minimal))
        latest = saved_offer(client, saved)["latest"]
        assert latest["shipping_cents"] == 0
        assert latest["total_cents"] == 18900
        assert latest["price_per_tb"] == "10.50"
        assert started <= datetime.fromisoformat(latest["observed_at"]) <= datetime.now(UTC)
        assert not {"fee_cents", "availability"} & set(latest)


def test_a_refused_price_is_refused_on_its_field_and_saves_nothing(database_url: str) -> None:
    """What makes a price refused is the schema's (tests/unit/catalog/test_schemas.py)."""
    with TestClient(create_app()) as client:
        result = post(client, "/api/prices", entered(client, price_payload(condition="excellent")))
        assert result.status_code == 422
        assert result.json()["detail"][0]["loc"] == ["body", "condition"]
        assert client.get("/api/offers").json() == []


def test_recording_a_price_keeps_one_offer_per_store_mpn_and_condition(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        first = post(client, "/api/prices", entered(client, price_payload()))
        assert first.status_code == 201, first.text
        later = post(
            client,
            "/api/prices",
            entered(
                client,
                price_payload(
                    item_price_cents=17900,
                    observed_at="2026-09-22T12:00:00Z",
                    url="https://example.com/disk-v2",
                ),
            ),
        )
        offer = saved_offer(client, later)
        assert offer["id"] == first.json()["offer_id"]
        assert offer["url"] == "https://example.com/disk"
        assert [o["item_price_cents"] for o in offer["observations"]] == [18900, 17900]
        other_condition = post(
            client, "/api/prices", entered(client, price_payload(condition="new"))
        )
        other_seller = post(
            client, "/api/prices", entered(client, price_payload(seller="Other seller"))
        )
        ids = {offer["id"], other_condition.json()["offer_id"], other_seller.json()["offer_id"]}
        assert len(ids) == 3
        assert saved_offer(client, other_seller)["drive"]["id"] == offer["drive"]["id"]
        assert len(client.get("/api/offers").json()) == 3


def test_concurrent_first_prices_for_one_offer_create_a_single_offer(database_url: str) -> None:
    with TestClient(create_app()) as client:

        def submit(day: int) -> dict:
            response = post(
                client,
                "/api/prices",
                entered(
                    client,
                    price_payload(
                        item_price_cents=18900 + day, observed_at=f"2026-09-2{day}T12:00:00Z"
                    ),
                ),
            )
            assert response.status_code == 201, response.text
            return response.json()

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(submit, range(4)))
        assert len({result["offer_id"] for result in results}) == 1
        [offer] = with_history(client)
        assert len(offer["observations"]) == 4


def test_an_unchanged_price_only_updates_when_the_offer_was_last_checked(database_url: str) -> None:
    with TestClient(create_app()) as client:
        first = saved_offer(client, post(client, "/api/prices", entered(client, price_payload())))
        assert first["last_checked_at"] == "2026-09-21T12:00:00Z"
        same = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                entered(client, price_payload(observed_at="2026-09-22T12:00:00Z")),
            ),
        )
        assert len(same["observations"]) == 1
        assert same["last_checked_at"] == "2026-09-22T12:00:00Z"
        changed = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                entered(
                    client,
                    price_payload(item_price_cents=17900, observed_at="2026-09-23T12:00:00Z"),
                ),
            ),
        )
        assert [o["item_price_cents"] for o in changed["observations"]] == [18900, 17900]
        assert changed["last_checked_at"] == "2026-09-23T12:00:00Z"
        assert client.get(f"/api/offers/{first['id']}").json() == changed


def test_unknown_shipping_stays_distinct_from_free_while_totals_stay_known(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        unknown = saved_offer(
            client, post(client, "/api/prices", entered(client, price_payload(shipping_cents=None)))
        )["latest"]
        assert unknown["shipping_cents"] is None
        assert unknown["shipping_known"] is False
        assert unknown["total_cents"] == 18900
        assert unknown["price_per_tb"] == "10.50"
        free_payload = price_payload(seller="Free shipper")
        del free_payload["shipping_cents"]
        free = saved_offer(client, post(client, "/api/prices", entered(client, free_payload)))[
            "latest"
        ]
        assert (free["shipping_cents"], free["shipping_known"]) == (0, True)


def test_a_sold_out_offer_keeps_its_last_price_and_is_marked_out_of_stock(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        post(client, "/api/prices", entered(client, price_payload()))
        sold_out = price_payload(in_stock=False, observed_at="2026-09-22T12:00:00Z")
        del sold_out["item_price_cents"], sold_out["shipping_cents"]
        offer = saved_offer(client, post(client, "/api/prices", entered(client, sold_out)))
        assert len(offer["observations"]) == 2
        latest = offer["latest"]
        assert latest["in_stock"] is False
        assert (latest["item_price_cents"], latest["shipping_cents"], latest["total_cents"]) == (
            18900,
            1000,
            19900,
        )
        still_sold_out = {**sold_out, "observed_at": "2026-09-23T12:00:00Z"}
        again = saved_offer(client, post(client, "/api/prices", entered(client, still_sold_out)))
        assert len(again["observations"]) == 2
        assert again["last_checked_at"] == "2026-09-23T12:00:00Z"
        back = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                entered(
                    client,
                    price_payload(item_price_cents=18500, observed_at="2026-09-24T12:00:00Z"),
                ),
            ),
        )
        assert [o["in_stock"] for o in back["observations"]] == [True, False, True]
        never_priced = post(
            client, "/api/prices", entered(client, {**sold_out, "seller": "New seller"})
        )
        assert never_priced.status_code == 422
        assert never_priced.json()["detail"][0]["loc"] == ["body", "item_price_cents"]


def test_a_price_is_answered_with_what_was_done_and_the_ids_of_what_it_touched(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        first = post(client, "/api/prices", entered(client, price_payload()))
        [offer] = with_history(client)
        again = post(
            client,
            "/api/prices",
            entered(client, price_payload(observed_at="2026-09-22T12:00:00Z")),
        )

    assert first.status_code == 201, first.text
    assert first.json() == {
        "status": "recorded",
        "offer_id": offer["id"],
        "price_id": offer["latest"]["id"],
        "review_item_id": None,
    }
    # The same price seen again is only a check of the offer: no price was made.
    assert (again.status_code, again.json()) == (
        201,
        {"status": "recorded", "offer_id": offer["id"], "price_id": None, "review_item_id": None},
    )


def test_a_person_and_a_collector_record_prices_through_the_same_operation(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        collected = post(client, "/api/ingestions", collected_payload())
        manual = post(
            client,
            "/api/prices",
            entered(client, price_payload(store="serverpartdeals", seller="x")),
        )
        by_seller = {offer["seller"]: offer for offer in client.get("/api/offers").json()}

    assert (collected.status_code, manual.status_code) == (201, 201)
    # Both are under the same store: who submitted a price is kept apart from where it was seen.
    assert {offer["store"] for offer in by_seller.values()} == {"serverpartdeals"}
    assert by_seller[""]["latest"]["provenance"] == "collected"
    assert by_seller["x"]["latest"]["provenance"] == "manual"


def test_a_price_can_name_the_offer_it_is_for_instead_of_describing_it(database_url: str) -> None:
    check = {"item_price_cents": 17900, "observed_at": "2026-09-22T12:00:00Z"}
    with TestClient(create_app()) as client:
        offer_id = post(client, "/api/prices", entered(client, price_payload())).json()["offer_id"]
        named = post(client, "/api/prices", entered(client, {"offer_id": offer_id, **check}))
        [offer] = with_history(client)
        missing = post(client, "/api/prices", entered(client, {"offer_id": str(uuid4()), **check}))

    assert named.status_code == 201, named.text
    assert named.json()["offer_id"] == offer_id == offer["id"]
    assert [price["item_price_cents"] for price in offer["observations"]] == [18900, 17900]
    # Shipping stays what the entry says, as for any price: free unless given.
    assert offer["latest"]["shipping_cents"] == 0
    assert (missing.status_code, missing.json()["detail"]) == (404, "Offer not found")


def test_a_price_whose_recording_fails_partway_leaves_nothing_behind(database_url: str) -> None:
    # The other MPNs a collector names for a drive are kept last: make keeping them fail.
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION refuse() RETURNS trigger AS $$"
                " BEGIN RAISE EXCEPTION 'aliases cannot be kept'; END $$ LANGUAGE plpgsql"
            )
        )
        connection.execute(
            text("CREATE TRIGGER refuse BEFORE INSERT ON mpn_aliases EXECUTE FUNCTION refuse()")
        )
    engine.dispose()
    key = str(uuid4())
    payload = collected_payload(aliases=["ST18000NM000J-2E3101"], brand="Seagate")
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        post(client, "/api/ingestions", collected_payload(mpn=None))
        failed = post(client, "/api/ingestions", payload, key)
        offers = client.get("/api/offers").json()
        queue = client.get("/api/review-items").json()
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(text("DROP TRIGGER refuse ON mpn_aliases"))
            drives = connection.execute(text("SELECT count(*) FROM drives")).scalar_one()
        engine.dispose()
        retried = post(client, "/api/ingestions", payload, key)

    assert failed.status_code == 500
    # No offer, no drive, and the offer still waits for review as it did before.
    assert (offers, drives, len(queue)) == ([], 0, 1)
    # The save key was not spent on the failure: the retry does the work.
    assert (retried.status_code, retried.json()["status"]) == (201, "recorded")


LEGACY_RESULT = {"id": str(uuid4()), "mpn": "ST18000NM000J", "observations": []}


def test_a_save_key_spent_before_prices_were_unified_is_refused_without_writing(
    database_url: str,
) -> None:
    """Its receipt holds a whole offer and a fingerprint made another way, so the request cannot
    be told from the one it answered: it is a conflict to reconcile, never a second write."""
    key = str(uuid4())
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO save_receipts (id, fingerprint, result)"
                    " VALUES (:id, :fingerprint, CAST(:result AS jsonb))"
                ),
                {"id": key, "fingerprint": "0" * 64, "result": json.dumps(LEGACY_RESULT)},
            )
        retried = post(client, "/api/prices", entered(client, price_payload()), key=key)
        again = post(client, "/api/prices", entered(client, price_payload()), key=key)
        offers = client.get("/api/offers").json()
    engine.dispose()
    assert (retried.status_code, again.status_code) == (409, 409)
    assert retried.json() == {
        "detail": "This save key was used before prices were recorded this way, so this request"
        " cannot be matched to the one it answered. Nothing was saved: check whether the price"
        " is already recorded, then save it under a new key."
    }
    assert offers == []


def test_a_price_for_a_named_offer_sent_twice_under_one_key_is_recorded_once(
    database_url: str,
) -> None:
    """As a recheck whose answer was lost is sent again: answered as it was, one price kept."""
    with TestClient(create_app()) as client:
        offer_id = post(client, "/api/prices", entered(client, price_payload())).json()["offer_id"]
        recheck = {"offer_id": offer_id, "provenance": "collected", "item_price_cents": 17900,
                   "observed_at": "2026-09-22T12:00:00Z"}  # fmt: skip
        key = str(uuid4())
        first = post(client, "/api/prices", entered(client, recheck), key)
        again = post(client, "/api/prices", entered(client, recheck), key)
        other = post(
            client, "/api/prices", entered(client, {**recheck, "item_price_cents": 16900}), key
        )
        prices = client.get(f"/api/offers/{offer_id}").json()["observations"]

    assert (first.status_code, again.status_code, again.json()) == (201, 201, first.json())
    assert other.status_code == 409
    assert [price["item_price_cents"] for price in prices] == [18900, 17900]
