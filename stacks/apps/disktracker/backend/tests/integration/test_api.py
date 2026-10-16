import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine, text

from disktracker.main import create_app


def post(
    client: TestClient, path: str, payload: dict[str, Any], key: str | None = None
) -> Response:
    return client.post(path, json=payload, headers={"Idempotency-Key": key or str(uuid4())})


def saved_offer(client: TestClient, recorded: Response) -> dict[str, Any]:
    """The offer a recorded price is for, with every price it has had."""
    assert recorded.status_code == 201, recorded.text
    offer: dict[str, Any] = client.get(f"/api/offers/{recorded.json()['offer_id']}").json()
    return offer


def with_history(client: TestClient) -> list[dict[str, Any]]:
    """Every offer with its full price history, fetched the way the app does."""
    ids = [offer["id"] for offer in client.get("/api/offers").json()]
    return [client.get(f"/api/offers/{offer_id}").json() for offer_id in ids]


def price_payload(**fields: Any) -> dict[str, Any]:
    return {
        "mpn": "ST18000NM000J",
        "store": "other",
        "seller": "Example seller",
        "condition": "manufacturer_recertified",
        "title": "Seagate Exos X18",
        "url": "https://example.com/disk",
        "capacity_gb": 18000,
        "item_price_cents": 18900,
        "shipping_cents": 1000,
        "observed_at": "2026-09-21T12:00:00Z",
        "notes": "Checked the selected 18 TB variant",
        **fields,
    }


def test_offers_are_identified_by_store_and_optional_marketplace_seller(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        direct = post(client, "/api/prices", price_payload(store="serverpartdeals", seller=""))
        assert direct.status_code == 201, direct.text
        direct_offer = saved_offer(client, direct)
        assert (direct_offer["store"], direct_offer["seller"]) == ("serverpartdeals", "")
        again = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                price_payload(
                    store="serverpartdeals", seller="  ", observed_at="2026-09-22T12:00:00Z"
                ),
            ),
        )
        assert again["id"] == direct_offer["id"]
        beach_audio = saved_offer(
            client, post(client, "/api/prices", price_payload(seller="Beach Audio"))
        )
        drivedeals = saved_offer(
            client, post(client, "/api/prices", price_payload(seller="drivedeals"))
        )
        assert len({direct_offer["id"], beach_audio["id"], drivedeals["id"]}) == 3
        assert post(client, "/api/prices", price_payload(store="frys")).status_code == 422
        assert post(client, "/api/prices", price_payload(store="newegg")).status_code == 422
        unnamed = post(client, "/api/prices", price_payload(store="other", seller=""))
        assert unnamed.status_code == 422
        assert unnamed.json()["detail"][0]["loc"] == ["body", "seller"]
        named = post(client, "/api/prices", price_payload(store="other", seller="Local shop"))
        assert named.status_code == 201, named.text


def test_offer_and_later_price_survive_a_new_application_instance(database_url: str) -> None:
    with TestClient(create_app()) as client:
        started = datetime.now(UTC)
        result = post(client, "/api/prices", price_payload())
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
            price_payload(item_price_cents=17900, observed_at="2026-09-22T12:00:00Z"),
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
        offer = saved_offer(client, post(client, "/api/prices", price_payload()))
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
        first = post(client, "/api/prices", price_payload(), key)
        retry = post(client, "/api/prices", price_payload(), key)
        assert retry.status_code == 201
        assert retry.json() == first.json()
        assert len(with_history(client)[0]["observations"]) == 1
        changed = post(client, "/api/prices", price_payload(item_price_cents=1), key)
        assert changed.status_code == 409


def test_concurrent_retries_record_one_price(database_url: str) -> None:
    key = str(uuid4())
    with TestClient(create_app()) as client:

        def submit() -> dict[str, Any]:
            response = post(client, "/api/prices", price_payload(), key)
            assert response.status_code == 201
            return response.json()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first, second = list(executor.map(lambda _: submit(), range(2)))
        assert first == second
        assert len(with_history(client)[0]["observations"]) == 1


def test_backdated_prices_preserve_the_latest_observation(database_url: str) -> None:
    with TestClient(create_app()) as client:
        post(client, "/api/prices", price_payload())
        older = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                price_payload(item_price_cents=10000, observed_at="2026-09-20T12:00:00Z"),
            ),
        )
        assert older["latest"]["item_price_cents"] == 18900
        assert [o["item_price_cents"] for o in older["observations"]] == [10000, 18900]


def test_a_price_left_without_shipping_or_time_is_free_and_seen_now(database_url: str) -> None:
    with TestClient(create_app()) as client:
        started = datetime.now(UTC)
        minimal = price_payload()
        for field in ("shipping_cents", "observed_at", "notes"):
            del minimal[field]
        saved = post(client, "/api/prices", minimal)
        latest = saved_offer(client, saved)["latest"]
        assert latest["shipping_cents"] == 0
        assert latest["total_cents"] == 18900
        assert latest["price_per_tb"] == "10.50"
        assert started <= datetime.fromisoformat(latest["observed_at"]) <= datetime.now(UTC)
        assert not {"fee_cents", "availability"} & set(latest)


def test_a_refused_price_is_refused_on_its_field_and_saves_nothing(database_url: str) -> None:
    """What makes a price refused is the schema's (tests/unit/catalog/test_schemas.py)."""
    with TestClient(create_app()) as client:
        result = post(client, "/api/prices", price_payload(condition="excellent"))
        assert result.status_code == 422
        assert result.json()["detail"][0]["loc"] == ["body", "condition"]
        assert client.get("/api/offers").json() == []


def test_missing_offer_returns_404(database_url: str) -> None:
    with TestClient(create_app()) as client:
        assert client.get(f"/api/offers/{uuid4()}").status_code == 404


def test_recording_a_price_keeps_one_offer_per_store_mpn_and_condition(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        first = post(client, "/api/prices", price_payload())
        assert first.status_code == 201, first.text
        later = post(
            client,
            "/api/prices",
            price_payload(
                item_price_cents=17900,
                observed_at="2026-09-22T12:00:00Z",
                url="https://example.com/disk-v2",
            ),
        )
        offer = saved_offer(client, later)
        assert offer["id"] == first.json()["offer_id"]
        assert offer["url"] == "https://example.com/disk"
        assert [o["item_price_cents"] for o in offer["observations"]] == [18900, 17900]
        other_condition = post(client, "/api/prices", price_payload(condition="new"))
        other_seller = post(client, "/api/prices", price_payload(seller="Other seller"))
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
                price_payload(
                    item_price_cents=18900 + day, observed_at=f"2026-09-2{day}T12:00:00Z"
                ),
            )
            assert response.status_code == 201, response.text
            return response.json()

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(submit, range(4)))
        assert len({result["offer_id"] for result in results}) == 1
        [offer] = with_history(client)
        assert len(offer["observations"]) == 4


def test_deleting_a_wrong_price_removes_it_and_deleting_the_last_price_removes_the_offer(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        post(client, "/api/prices", price_payload())
        typo = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                price_payload(item_price_cents=1890, observed_at="2026-09-22T12:00:00Z"),
            ),
        )
        wrong, right = typo["observations"][1]["id"], typo["observations"][0]["id"]
        deleted = client.delete(f"/api/prices/{wrong}")
        kept = client.get(f"/api/offers/{typo['id']}").json()
        # A price already gone is gone: deleting it again, or one never kept, is no error.
        again = client.delete(f"/api/prices/{wrong}")
        never = client.delete(f"/api/prices/{uuid4()}")
        malformed = client.delete("/api/prices/not-a-price")
        last = client.delete(f"/api/prices/{right}")
        offers = client.get("/api/offers").json()
    assert (deleted.status_code, deleted.content) == (204, b"")
    assert [o["item_price_cents"] for o in kept["observations"]] == [18900]
    assert kept["latest"]["item_price_cents"] == 18900
    assert (again.status_code, never.status_code, malformed.status_code) == (204, 204, 422)
    # Its last price gone, the offer goes with it.
    assert (last.status_code, offers) == (204, [])


def test_deleting_an_offer_removes_it_and_its_prices(database_url: str) -> None:
    with TestClient(create_app()) as client:
        offer = saved_offer(client, post(client, "/api/prices", price_payload()))
        kept = saved_offer(
            client, post(client, "/api/prices", price_payload(seller="Other seller"))
        )
        assert client.delete(f"/api/offers/{offer['id']}").status_code == 204
        assert [o["id"] for o in client.get("/api/offers").json()] == [kept["id"]]
        assert client.delete(f"/api/offers/{offer['id']}").status_code == 404


def test_editing_an_offer_updates_its_details_in_place(database_url: str) -> None:
    with TestClient(create_app()) as client:
        offer = saved_offer(client, post(client, "/api/prices", price_payload()))
        path = f"/api/offers/{offer['id']}"
        edited = client.patch(path, json={"title": "Exos X18 18TB", "url": None})
        assert edited.status_code == 200, edited.text
        assert edited.json()["title"] == "Exos X18 18TB"
        assert edited.json()["url"] is None
        assert client.get(path).json() == edited.json()
        assert client.patch(path, json={"seller": "Someone else"}).status_code == 422
        assert client.patch(path, json={"capacity_gb": 20000}).status_code == 422
        assert client.patch(f"/api/offers/{uuid4()}", json={"title": "x"}).status_code == 404


def test_replacing_a_drives_plain_specifications_updates_every_offer_for_that_mpn(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        offer = saved_offer(client, post(client, "/api/prices", price_payload()))
        assert offer["drive"]["specifications"] == {
            "media_type": "unknown",
            "form_factor": "unknown",
            "interface": "unknown",
            "recording_type": "unknown",
            "intended_use": [],
        }
        post(client, "/api/prices", price_payload(seller="Other seller"))
        path = f"/api/drives/{offer['drive']['id']}"
        specifications = {
            "media_type": "hdd",
            "form_factor": "3_5",
            "interface": "sata",
            "recording_type": "cmr",
            "intended_use": ["nas"],
        }
        saved = client.patch(path, json={"capacity_gb": 20000, "specifications": specifications})
        assert saved.status_code == 200, saved.text
        assert saved.json()["specifications"] == specifications
        assert saved.json()["capacity_gb"] == 20000
        offers = client.get("/api/offers").json()
        assert [o["drive"]["specifications"] for o in offers] == [specifications, specifications]
        assert {o["latest"]["price_per_tb"] for o in offers} == {"9.95"}
        for rejected in (
            {**specifications, "interface": "sata-express"},
            {**specifications, "recording_type": {"value": "cmr", "verification": "verified"}},
            {**specifications, "intended_use": ["nas", "toaster"]},
            {**specifications, "media_type": "floppy"},
            {**specifications, "form_factor": "5_25"},
        ):
            response = client.patch(path, json={"capacity_gb": 20000, "specifications": rejected})
            assert response.status_code == 422, rejected
        missing = client.patch(
            f"/api/drives/{uuid4()}",
            json={"capacity_gb": 20000, "specifications": specifications},
        )
        assert missing.status_code == 404


def test_a_drives_brand_is_corrected_by_hand_and_then_left_alone_by_the_collector(
    database_url: str,
) -> None:
    specifications = {
        "media_type": "hdd",
        "form_factor": "3_5",
        "interface": "sata",
        "recording_type": "cmr",
        "intended_use": [],
    }
    with TestClient(create_app()) as client:
        drive = post(client, "/api/prices", scraped_payload(brand="Dell")).json()
        offer = client.get("/api/offers").json()[0]
        path = f"/api/drives/{offer['drive']['id']}"
        body = {"capacity_gb": 18000, "specifications": specifications}
        named = client.patch(path, json={**body, "brand": "  Seagate "})
        post(
            client,
            "/api/prices",
            scraped_payload(brand="Dell", observed_at="2026-09-23T12:00:00Z"),
        )
        after_a_run = client.get("/api/offers").json()[0]["drive"]["brand"]
        # Left out, the brand stays; blank clears it, for a source to name it again.
        untouched = client.patch(path, json=body)
        cleared = client.patch(path, json={**body, "brand": "  "})
        too_long = client.patch(path, json={**body, "brand": "x" * 61})

    assert drive["status"] == "recorded"
    assert (named.status_code, named.json()["brand"]) == (200, "Seagate")
    assert (after_a_run, untouched.json()["brand"]) == ("Seagate", "Seagate")
    assert (cleared.json()["brand"], too_long.status_code) == (None, 422)


def test_capacity_belongs_to_the_drive_so_every_offer_for_an_mpn_shares_it(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        first = saved_offer(client, post(client, "/api/prices", price_payload()))
        assert first["capacity_gb"] == 18000
        assert first["drive"]["capacity_gb"] == 18000
        reused = post(client, "/api/prices", price_payload(seller="Other seller", capacity_gb=None))
        assert saved_offer(client, reused)["capacity_gb"] == 18000
        assert saved_offer(client, reused)["latest"]["price_per_tb"] == "11.06"
        mismatch = post(client, "/api/prices", price_payload(seller="Third", capacity_gb=20000))
        assert mismatch.status_code == 409
        assert mismatch.json()["detail"] == (
            "MPN ST18000NM000J is recorded as 18 TB."
            " Edit the drive's specifications to change its capacity."
        )
        unknown = post(client, "/api/prices", price_payload(mpn="ST20000NM007D", capacity_gb=None))
        assert unknown.status_code == 422
        assert unknown.json()["detail"][0]["loc"] == ["body", "capacity_gb"]
        assert len(client.get("/api/offers").json()) == 2


def test_later_prices_never_overwrite_the_title_or_url_an_offer_was_created_with(
    database_url: str,
) -> None:
    untitled = price_payload()
    del untitled["title"]
    with TestClient(create_app()) as client:
        first = post(client, "/api/prices", untitled)
        assert saved_offer(client, first)["title"] == "ST18000NM000J"
        client.patch(f"/api/offers/{first.json()['offer_id']}", json={"title": "Exos X18"})
        later = post(client, "/api/prices", {**untitled, "observed_at": "2026-09-22T12:00:00Z"})
        assert saved_offer(client, later)["title"] == "Exos X18"
        retitled = post(
            client,
            "/api/prices",
            price_payload(title="Scraped title", url="https://example.com/?ref=1"),
        )
        assert saved_offer(client, retitled)["title"] == "Exos X18"
        assert saved_offer(client, retitled)["url"] == "https://example.com/disk"


def test_an_unchanged_price_only_updates_when_the_offer_was_last_checked(database_url: str) -> None:
    with TestClient(create_app()) as client:
        first = saved_offer(client, post(client, "/api/prices", price_payload()))
        assert first["last_checked_at"] == "2026-09-21T12:00:00Z"
        same = saved_offer(
            client, post(client, "/api/prices", price_payload(observed_at="2026-09-22T12:00:00Z"))
        )
        assert len(same["observations"]) == 1
        assert same["last_checked_at"] == "2026-09-22T12:00:00Z"
        changed = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                price_payload(item_price_cents=17900, observed_at="2026-09-23T12:00:00Z"),
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
            client, post(client, "/api/prices", price_payload(shipping_cents=None))
        )["latest"]
        assert unknown["shipping_cents"] is None
        assert unknown["shipping_known"] is False
        assert unknown["total_cents"] == 18900
        assert unknown["price_per_tb"] == "10.50"
        free_payload = price_payload(seller="Free shipper")
        del free_payload["shipping_cents"]
        free = saved_offer(client, post(client, "/api/prices", free_payload))["latest"]
        assert (free["shipping_cents"], free["shipping_known"]) == (0, True)


def test_a_sold_out_offer_keeps_its_last_price_and_is_marked_out_of_stock(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        post(client, "/api/prices", price_payload())
        sold_out = price_payload(in_stock=False, observed_at="2026-09-22T12:00:00Z")
        del sold_out["item_price_cents"], sold_out["shipping_cents"]
        offer = saved_offer(client, post(client, "/api/prices", sold_out))
        assert len(offer["observations"]) == 2
        latest = offer["latest"]
        assert latest["in_stock"] is False
        assert (latest["item_price_cents"], latest["shipping_cents"], latest["total_cents"]) == (
            18900,
            1000,
            19900,
        )
        still_sold_out = {**sold_out, "observed_at": "2026-09-23T12:00:00Z"}
        again = saved_offer(client, post(client, "/api/prices", still_sold_out))
        assert len(again["observations"]) == 2
        assert again["last_checked_at"] == "2026-09-23T12:00:00Z"
        back = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                price_payload(item_price_cents=18500, observed_at="2026-09-24T12:00:00Z"),
            ),
        )
        assert [o["in_stock"] for o in back["observations"]] == [True, False, True]
        never_priced = post(client, "/api/prices", {**sold_out, "seller": "New seller"})
        assert never_priced.status_code == 422
        assert never_priced.json()["detail"][0]["loc"] == ["body", "item_price_cents"]


def test_mpns_are_normalized_so_spacing_and_case_do_not_split_a_drive(database_url: str) -> None:
    with TestClient(create_app()) as client:
        first = saved_offer(
            client, post(client, "/api/prices", price_payload(mpn=" st18000 nm000j "))
        )
        assert first["mpn"] == "ST18000NM000J"
        second = saved_offer(
            client, post(client, "/api/prices", price_payload(seller="Other seller"))
        )
        assert second["drive"]["id"] == first["drive"]["id"]
        assert first["drive"]["aliases"] == []


def test_an_alias_merges_a_variant_mpn_into_its_drive_and_routes_later_prices(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        variant = post(
            client, "/api/prices", price_payload(mpn="ST18000NM000J-2E3101", seller="Shop A")
        ).json()
        post(
            client,
            "/api/prices",
            price_payload(mpn="ST18000NM000J-2E3101", item_price_cents=17000, seller="Shop B"),
        )
        canonical = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                price_payload(seller="Shop B", observed_at="2026-09-20T12:00:00Z"),
            ),
        )
        path = f"/api/drives/{canonical['drive']['id']}/aliases"
        added = client.post(path, json={"mpn": "st18000nm000j-2e3101"})
        assert added.status_code == 201, added.text
        assert added.json()["aliases"] == ["ST18000NM000J-2E3101"]
        offers = {o["seller"]: o for o in with_history(client)}
        assert set(offers) == {"Shop A", "Shop B"}
        assert {o["mpn"] for o in offers.values()} == {"ST18000NM000J"}
        assert {o["drive"]["id"] for o in offers.values()} == {canonical["drive"]["id"]}
        assert [o["item_price_cents"] for o in offers["Shop B"]["observations"]] == [18900, 17000]
        later = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                price_payload(
                    mpn="ST18000NM000J-2E3101",
                    item_price_cents=16000,
                    seller="Shop A",
                    observed_at="2026-09-25T12:00:00Z",
                ),
            ),
        )
        assert later["id"] == variant["offer_id"]
        assert later["mpn"] == "ST18000NM000J"
        assert client.post(path, json={"mpn": "ST18000NM000J"}).status_code == 409
        missing = client.post(f"/api/drives/{uuid4()}/aliases", json={"mpn": "X"})
        assert missing.status_code == 404


def scraped_payload(**fields: Any) -> dict[str, Any]:
    return {
        "provenance": "collected",
        "on_unmatched": "queue",
        "store": "serverpartdeals",
        "url": "https://www.serverpartdeals.com/products/seagate-exos-x18",
        "title": "Seagate Exos X18 ST18000NM000J 18TB Recertified",
        "seller": "",
        "mpn": "ST18000NM000J",
        "condition": "manufacturer_recertified",
        "capacity_gb": 18000,
        "item_price_cents": 36999,
        "shipping_cents": 0,
        "in_stock": True,
        "observed_at": "2026-09-21T12:00:00Z",
        **fields,
    }


def test_the_review_queue_can_be_read_a_part_at_a_time_by_store_and_reason(
    database_url: str,
) -> None:
    """So whatever works through a long queue, a person or a program, can take it in batches."""
    with TestClient(create_app()) as client:
        for number, (source, mpn, condition) in enumerate(
            [
                ("serverpartdeals", None, "new"),
                ("goharddrive", None, "new"),
                ("goharddrive", "ST18000NM000J", None),
                ("goharddrive", None, "new"),
            ]
        ):
            queued = client.post(
                "/api/prices",
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
            answer = client.get("/api/review-items", params=query)
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
            client.get("/api/review-items", params=query).status_code
            for query in ({"limit": 0}, {"limit": 501}, {"offset": -1}, {"reason": "bored"})
        ]
        assert refused == [422, 422, 422, 422]


def test_a_sold_out_scraped_offer_records_only_that_it_is_out_of_stock(
    database_url: str,
) -> None:
    placeholder = {"in_stock": False, "item_price_cents": 1_000_000}
    with TestClient(create_app()) as client:
        unseen = post(client, "/api/prices", scraped_payload(**placeholder))
        nothing = client.get("/api/offers").json()
        post(client, "/api/prices", scraped_payload())
        sold_out = post(
            client,
            "/api/prices",
            scraped_payload(**placeholder, observed_at="2026-09-22T12:00:00Z"),
        )
        [offer] = client.get("/api/offers").json()

    # Never seen in stock, it has no real price to track yet.
    assert (unseen.status_code, unseen.json()["status"], nothing) == (200, "ignored", [])
    assert sold_out.json()["status"] == "recorded"
    # Sold out, it keeps the price it last had in stock: the store's sold-out price is ignored.
    assert (offer["latest"]["in_stock"], offer["latest"]["item_price_cents"]) == (False, 36999)
    assert offer["last_checked_at"] == "2026-09-22T12:00:00Z"


def test_a_scraped_offer_with_an_mpn_and_condition_is_recorded_as_a_sourced_price(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        result = post(client, "/api/prices", scraped_payload())
        assert result.status_code == 201, result.text
        assert result.json()["status"] == "recorded"
        [offer] = client.get("/api/offers").json()
        assert result.json()["offer_id"] == offer["id"]
        assert (offer["mpn"], offer["store"], offer["condition"]) == (
            "ST18000NM000J",
            "serverpartdeals",
            "manufacturer_recertified",
        )
        assert offer["latest"]["item_price_cents"] == 36999
        assert offer["latest"]["provenance"] == "collected"
        manual = saved_offer(
            client, post(client, "/api/prices", price_payload(seller="Manual shop"))
        )
        assert manual["latest"]["provenance"] == "manual"


def test_scraped_offers_that_cannot_be_matched_wait_in_the_review_queue(database_url: str) -> None:
    base = "https://www.serverpartdeals.com/products/"
    with TestClient(create_app()) as client:
        first = post(client, "/api/prices", scraped_payload(mpn=None, url=base + "mystery"))
        assert first.status_code == 202, first.text
        assert first.json()["status"] == "queued"
        again = post(
            client,
            "/api/prices",
            scraped_payload(
                mpn=None,
                url=base + "mystery",
                item_price_cents=35999,
                observed_at="2026-09-22T12:00:00Z",
            ),
        )
        assert again.json()["review_item_id"] == first.json()["review_item_id"]
        post(client, "/api/prices", scraped_payload(url=base + "odd-condition", condition=None))
        post(client, "/api/prices", scraped_payload())
        post(
            client,
            "/api/prices",
            scraped_payload(url=base + "wrong-capacity", seller="x", capacity_gb=20000),
        )
        post(
            client,
            "/api/prices",
            scraped_payload(url=base + "new-drive", mpn="ST20000NM007D", capacity_gb=None),
        )
        queue = {item["url"]: item for item in client.get("/api/review-items").json()}
        assert {url.removeprefix(base): item["reason"] for url, item in queue.items()} == {
            "mystery": "missing_mpn",
            "odd-condition": "missing_condition",
            "wrong-capacity": "capacity_conflict",
            "new-drive": "missing_capacity",
        }
        mystery = queue[base + "mystery"]
        assert (mystery["store"], mystery["title"]) == (
            "serverpartdeals",
            scraped_payload()["title"],
        )
        assert (mystery["item_price_cents"], mystery["last_seen_at"]) == (
            35999,
            "2026-09-22T12:00:00Z",
        )
        assert len(client.get("/api/offers").json()) == 1


def test_a_collected_offer_no_single_drive_could_be_waits_for_a_person_to_say_what_it_is(
    database_url: str,
) -> None:
    """Which titles and capacities are doubted is the catalog rules'
    (tests/unit/catalog/test_rules.py); this is what becomes of an offer that is."""
    base = "https://www.serverorbit.com/products/"
    bundle = scraped_payload(
        url=base + "bundle", mpn="Q1J18A", title="HPE Q1J18A 45TB Bundle D3710 25x1.8TB SAS",
        capacity_gb=45000,
    )  # fmt: skip
    huge = scraped_payload(
        url=base + "kioxia", mpn="KPM7XVUG960G", title="Kioxia KPM7XVUG960G 960TB SAS Read Intensive",
        capacity_gb=960000,
    )  # fmt: skip
    with TestClient(create_app()) as client:
        queued = [post(client, "/api/prices", entry) for entry in (bundle, huge)]
        queue = {item["url"]: item["reason"] for item in client.get("/api/review-items").json()}
        # A person says what the second one is: a 960 GB drive.
        decided = client.put(
            f"/api/review-items/{queued[1].json()['review_item_id']}/decision",
            json={"decision": "match", "mpn": "KPM7XVUG960G", "condition": "new",
                  "capacity_gb": 960},
        )  # fmt: skip
        later = post(client, "/api/prices", {**huge, "observed_at": "2026-09-22T12:00:00Z"})
        # Entered by hand, it is what the person says it is.
        entered = post(
            client,
            "/api/prices",
            price_payload(mpn="R0P90A", title="HPE R0P90A 48TB (8x6) 6-pack", capacity_gb=48000),
        )

    assert [answer.json()["status"] for answer in queued] == ["queued", "queued"]
    assert queue == {base + "bundle": "not_a_single_drive", base + "kioxia": "implausible_capacity"}
    assert decided.status_code == 200, decided.text
    assert (later.status_code, later.json()["status"]) == (201, "recorded")
    assert entered.status_code == 201, entered.text


def test_a_queued_offer_leaves_the_review_queue_once_a_later_scrape_of_it_is_recorded(
    database_url: str,
) -> None:
    base = "https://www.serverpartdeals.com/products/"
    with TestClient(create_app()) as client:
        post(client, "/api/prices", scraped_payload(mpn=None, url=base + "mystery"))
        post(client, "/api/prices", scraped_payload(mpn=None, url=base + "another"))
        later = post(client, "/api/prices", scraped_payload(url=base + "mystery"))
        assert later.status_code == 201, later.text
        assert [item["url"] for item in client.get("/api/review-items").json()] == [
            base + "another"
        ]


def test_a_capacity_conflict_is_shown_with_the_drive_and_settled_either_way(
    database_url: str,
) -> None:
    """A reviewer sees the drive an offer's MPN names beside what was collected, and says which
    capacity is right: the drive's, so the offer is recorded as that drive; or the offer's, so
    the drive is corrected for every offer of it, in the same decision."""
    base = "https://www.serverorbit.com/products/"
    mpn = "P09094-H21"
    with TestClient(create_app()) as client:
        # Recorded long ago with a capacity misread from its title.
        stored = post(client, "/api/prices", price_payload(mpn=mpn, capacity_gb=213200))
        conflicts = [
            post(client, "/api/prices", scraped_payload(url=base + name, mpn=mpn,
                 title=f"HPE {mpn} 3.2TB SAS", capacity_gb=3200, condition="refurbished",
                 seller=name)).json()["review_item_id"]
            for name in ("kept", "corrected", "refused")
        ]  # fmt: skip
        unnamed = post(client, "/api/prices", scraped_payload(url=base + "unnamed", mpn=None))
        queue = {item["id"]: item for item in client.get("/api/review-items").json()}

        def decide(item: str, **decision: Any) -> Any:
            body = {"decision": "match", "mpn": mpn, "condition": "refurbished", **decision}
            return client.put(f"/api/review-items/{item}/decision", json=body)

        refused = decide(conflicts[2], capacity_gb=3200)
        unsaid = decide(conflicts[2], correct_drive=True)
        kept = decide(conflicts[0])
        drive_kept = client.get(f"/api/offers/{kept.json()['offer_id']}").json()["drive"]
        corrected = decide(conflicts[1], capacity_gb=3200, correct_drive=True)
        first = client.get(f"/api/offers/{stored.json()['offer_id']}").json()

    assert queue[conflicts[0]]["drive"]["mpn"] == mpn
    assert queue[conflicts[0]]["drive"]["capacity_gb"] == 213200
    assert queue[unnamed.json()["review_item_id"]]["drive"] is None
    # A capacity other than the drive's is refused unless the drive is to be corrected.
    assert refused.status_code == 409, refused.text
    assert unsaid.status_code == 422
    assert [issue["loc"] for issue in unsaid.json()["detail"]] == [["body", "capacity_gb"]]
    assert kept.status_code == 200, kept.text
    assert drive_kept["capacity_gb"] == 213200
    assert corrected.status_code == 200, corrected.text
    # Corrected for every offer of the drive, the one recorded long ago too.
    assert (first["drive"]["capacity_gb"], first["capacity_gb"]) == (3200, 3200)


def test_resolving_a_queued_offer_records_it_and_later_scrapes_match_directly(
    database_url: str,
) -> None:
    url = "https://www.serverpartdeals.com/products/mystery"
    with TestClient(create_app()) as client:
        queued = post(client, "/api/prices", scraped_payload(mpn=None, condition=None, url=url))
        item_id = queued.json()["review_item_id"]
        resolved = client.put(
            f"/api/review-items/{item_id}/decision",
            json={
                "decision": "match",
                "mpn": "st18000nm000j",
                "condition": "manufacturer_recertified",
                "capacity_gb": 18000,
            },
        )
        assert resolved.status_code == 200, resolved.text
        offer = client.get(f"/api/offers/{resolved.json()['offer_id']}").json()
        assert (offer["mpn"], offer["latest"]["item_price_cents"]) == ("ST18000NM000J", 36999)
        assert offer["latest"]["provenance"] == "collected"
        assert client.get("/api/review-items").json() == []
        later = post(
            client,
            "/api/prices",
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
        saved = client.get(f"/api/offers/{offer['id']}").json()
        assert [o["item_price_cents"] for o in saved["observations"]] == [36999, 34999]
        missing = client.put(
            f"/api/review-items/{uuid4()}/decision",
            json={"decision": "match", "mpn": "X", "condition": "new", "capacity_gb": 1000},
        )
        assert missing.status_code == 404


def test_ignoring_a_queued_offer_keeps_later_scrapes_of_it_out_of_the_queue(
    database_url: str,
) -> None:
    url = "https://www.serverpartdeals.com/products/not-a-drive"
    with TestClient(create_app()) as client:
        queued = post(client, "/api/prices", scraped_payload(mpn=None, url=url)).json()
        ignored = client.put(
            f"/api/review-items/{queued['review_item_id']}/decision", json={"decision": "ignore"}
        )
        assert ignored.status_code == 200, ignored.text
        assert client.get("/api/review-items").json() == []
        later = post(client, "/api/prices", scraped_payload(mpn=None, url=url))
        assert later.status_code == 200
        assert later.json() == {
            "status": "ignored",
            "offer_id": None,
            "price_id": None,
            "review_item_id": None,
        }
        assert client.get("/api/review-items").json() == []
        assert client.get("/api/offers").json() == []


def test_a_scraped_offer_can_declare_other_mpns_for_its_drive(database_url: str) -> None:
    base = "https://www.serverpartdeals.com/products/"
    with TestClient(create_app()) as client:
        oem = post(
            client,
            "/api/prices",
            scraped_payload(
                url=base + "dell-g14", mpn="0HNHWC", capacity_gb=16000, condition="new"
            ),
        ).json()
        maker = post(
            client,
            "/api/prices",
            scraped_payload(
                url=base + "bare",
                mpn="WUH721816AL5205",
                aliases=["0hnhwc"],
                capacity_gb=16000,
                condition="refurbished",
            ),
        )
        assert maker.status_code == 201, maker.text
        offers = {o["id"]: o for o in client.get("/api/offers").json()}
        assert {o["mpn"] for o in offers.values()} == {"WUH721816AL5205"}
        assert offers[oem["offer_id"]]["drive"]["aliases"] == ["0HNHWC"]
        again = post(
            client,
            "/api/prices",
            scraped_payload(
                url=base + "bare",
                mpn="WUH721816AL5205",
                aliases=["0HNHWC"],
                capacity_gb=16000,
                condition="refurbished",
                item_price_cents=35000,
                observed_at="2026-09-22T12:00:00Z",
            ),
        )
        assert again.status_code == 201, again.text
        later_oem = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                scraped_payload(
                    url=base + "dell-g13", mpn="0HNHWC", capacity_gb=16000, condition="used"
                ),
            ),
        )
        assert later_oem["mpn"] == ("WUH721816AL5205")


def test_a_scraped_alias_already_claimed_by_another_drive_is_left_for_a_person(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        claimed = saved_offer(
            client, post(client, "/api/prices", price_payload(mpn="ST18000NM000J"))
        )
        drive_id = claimed["drive"]["id"]
        assert (
            client.post(f"/api/drives/{drive_id}/aliases", json={"mpn": "0XYZ"}).status_code == 201
        )

        scraped = post(
            client,
            "/api/prices",
            scraped_payload(
                url="https://www.serverpartdeals.com/products/other",
                mpn="ST16000NM000J",
                aliases=["0XYZ"],
                capacity_gb=16000,
            ),
        )

        assert scraped.status_code == 201, scraped.text
        drives = {o["mpn"]: o["drive"]["aliases"] for o in client.get("/api/offers").json()}
        assert drives == {"ST18000NM000J": ["0XYZ"], "ST16000NM000J": []}


def schema_of(spec: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in reference:
        return spec["components"]["schemas"][reference["$ref"].rsplit("/", 1)[-1]]
    if reference.get("type") == "array":
        return schema_of(spec, reference["items"])
    return reference


def response_schema(spec: dict[str, Any], path: str, method: str, status: str) -> dict[str, Any]:
    content = spec["paths"][path][method]["responses"][status]["content"]
    return schema_of(spec, content["application/json"]["schema"])


def test_the_published_contract_describes_offers_prices_drives_and_review_items(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        spec = client.get("/openapi.json").json()

    operations = {
        (path, method): operation["operationId"]
        for path, methods in spec["paths"].items()
        for method, operation in methods.items()
    }
    assert {
        key: operations.get(key)
        for key in [
            ("/api/offers", "get"),
            ("/api/offers/{offer_id}", "get"),
            ("/api/offers/{offer_id}", "patch"),
            ("/api/offers/{offer_id}", "delete"),
            ("/api/prices", "post"),
            ("/api/prices/{price_id}", "delete"),
            ("/api/drives/{drive_id}", "patch"),
            ("/api/drives/{drive_id}/aliases", "post"),
            ("/api/review-items", "get"),
            ("/api/review-items/{item_id}/decision", "put"),
        ]
    } == {
        ("/api/offers", "get"): "list_offers",
        ("/api/offers/{offer_id}", "get"): "get_offer",
        ("/api/offers/{offer_id}", "patch"): "edit_offer",
        ("/api/offers/{offer_id}", "delete"): "delete_offer",
        ("/api/prices", "post"): "record_price",
        ("/api/prices/{price_id}", "delete"): "delete_price",
        ("/api/drives/{drive_id}", "patch"): "edit_drive",
        ("/api/drives/{drive_id}/aliases", "post"): "add_alias",
        ("/api/review-items", "get"): "review_items",
        ("/api/review-items/{item_id}/decision", "put"): "decide",
    }
    # Nothing is left of the routes these replaced.
    assert not [path for path in spec["paths"] if "listings" in path or "unmatched" in path]
    decided = response_schema(spec, "/api/review-items/{item_id}/decision", "put", "200")
    assert decided["properties"]["status"]["enum"] == ["matched", "ignored"]
    summary = response_schema(spec, "/api/offers", "get", "200")
    assert set(summary["required"]) == {
        "id", "title", "mpn", "store", "store_name", "seller", "url", "condition",
        "last_checked_at", "capacity_gb", "drive", "latest", "doubt",
    }  # fmt: skip
    listing = response_schema(spec, "/api/offers/{offer_id}", "get", "200")
    assert set(listing["required"]) == set(summary["required"]) | {"observations"}
    drive = schema_of(spec, listing["properties"]["drive"])
    assert set(drive["required"]) == {
        "id", "mpn", "aliases", "brand", "capacity_gb", "specifications",
    }  # fmt: skip
    latest = schema_of(spec, listing["properties"]["latest"])
    assert set(latest["required"]) == {
        "id", "item_price_cents", "shipping_cents", "shipping_known", "in_stock", "observed_at",
        "entered_at", "notes", "provenance", "total_cents", "price_per_tb",
    }  # fmt: skip
    for status in ("201", "202", "200"):
        result = response_schema(spec, "/api/prices", "post", status)
        assert set(result["properties"]) == {"status", "offer_id", "price_id", "review_item_id"}
        assert result["properties"]["status"]["enum"] == ["recorded", "queued", "ignored"]
    queued = response_schema(spec, "/api/review-items", "get", "200")
    assert {"id", "store", "url", "reason", "first_seen_at", "last_seen_at"} <= set(
        queued["required"]
    )


def test_listings_carry_each_offers_latest_price_and_history_is_fetched_per_offer(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        first = saved_offer(client, post(client, "/api/prices", price_payload(seller="Shop A")))
        post(
            client,
            "/api/prices",
            price_payload(
                seller="Shop A", item_price_cents=17900, observed_at="2026-09-22T12:00:00Z"
            ),
        )
        other = saved_offer(client, post(client, "/api/prices", price_payload(seller="Shop B")))
        post(client, "/api/prices", price_payload(seller="Shop C"))

        summaries = client.get("/api/offers").json()
        histories = [client.get(f"/api/offers/{offer['id']}").json() for offer in (first, other)]

    assert all("observations" not in summary for summary in summaries)
    latest = {summary["seller"]: summary["latest"]["item_price_cents"] for summary in summaries}
    assert latest == {"Shop A": 17900, "Shop B": 18900, "Shop C": 18900}
    assert {
        history["seller"]: [o["item_price_cents"] for o in history["observations"]]
        for history in histories
    } == {"Shop A": [18900, 17900], "Shop B": [18900]}


def test_the_western_digital_store_is_a_store(database_url: str) -> None:
    with TestClient(create_app()) as client:
        saved = post(client, "/api/prices", price_payload(store="westerndigital", seller=""))
        [offer] = client.get("/api/offers").json()

    assert saved.status_code == 201, saved.text
    assert offer["store"] == "westerndigital"


def test_listings_can_be_narrowed_to_one_store(database_url: str) -> None:
    with TestClient(create_app()) as client:
        post(client, "/api/prices", price_payload(store="serverpartdeals", seller=""))
        post(client, "/api/prices", price_payload(store="other", seller="Shop"))

        narrowed = client.get("/api/offers", params={"store": "serverpartdeals"}).json()
        everything = client.get("/api/offers").json()
        unknown = client.get("/api/offers", params={"store": "frys"})

    assert [listing["store"] for listing in narrowed] == ["serverpartdeals"]
    assert sorted(listing["store"] for listing in everything) == ["other", "serverpartdeals"]
    # Stores are data now: a store nothing is recorded under simply lists nothing.
    assert (unknown.status_code, unknown.json()) == (200, [])


def test_small_drives_and_cards_are_tracked_in_whole_gigabytes(database_url: str) -> None:
    with TestClient(create_app()) as client:
        card = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                price_payload(
                    mpn="SDSQXAA-128G", capacity_gb=128, item_price_cents=1999, shipping_cents=0
                ),
            ),
        )
        tiny = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                price_payload(
                    mpn="SDSQUA4-032G", capacity_gb=32, item_price_cents=599, shipping_cents=0
                ),
            ),
        )

    assert (card["capacity_gb"], card["latest"]["price_per_tb"]) == (128, "156.17")
    assert (tiny["capacity_gb"], tiny["latest"]["price_per_tb"]) == (32, "187.19")


def test_a_scraped_offer_names_its_drive_s_brand_until_one_is_known(database_url: str) -> None:
    with TestClient(create_app()) as client:
        manual = post(client, "/api/prices", price_payload(mpn="WD120EFBX", capacity_gb=12000))
        assert saved_offer(client, manual)["drive"]["brand"] is None
        first = post(client, "/api/prices", scraped_payload(brand="Seagate"))
        later = post(
            client,
            "/api/prices",
            scraped_payload(
                brand="Dell", item_price_cents=35999, observed_at="2026-09-23T12:00:00Z"
            ),
        )
        unnamed = post(
            client,
            "/api/prices",
            scraped_payload(mpn="WD120EFBX", capacity_gb=12000, url="https://spd.test/wd"),
        )
        brands = {o["mpn"]: o["drive"]["brand"] for o in client.get("/api/offers").json()}
        too_long = post(client, "/api/prices", scraped_payload(brand="x" * 61))

    assert (first.status_code, later.status_code, unnamed.status_code) == (201, 201, 201)
    assert brands == {"ST18000NM000J": "Seagate", "WD120EFBX": None}
    assert too_long.status_code == 422


def test_a_scraped_offer_fills_in_specifications_nobody_has_entered(database_url: str) -> None:
    with TestClient(create_app()) as client:
        first = post(
            client,
            "/api/prices",
            scraped_payload(
                specifications={"media_type": "hdd", "form_factor": "3_5", "interface": "sas"}
            ),
        )
        assert first.status_code == 201, first.text
        drive = client.get(f"/api/offers/{first.json()['offer_id']}").json()["drive"]
        assert drive["specifications"] == {
            "media_type": "hdd",
            "form_factor": "3_5",
            "interface": "sas",
            "recording_type": "unknown",
            "intended_use": [],
        }
        entered = {**drive["specifications"], "interface": "sata", "intended_use": ["nas"]}
        client.patch(
            f"/api/drives/{drive['id']}",
            json={"capacity_gb": 18000, "specifications": entered},
        )

        later = post(
            client,
            "/api/prices",
            scraped_payload(
                item_price_cents=35999,
                observed_at="2026-09-23T12:00:00Z",
                specifications={"interface": "sas", "recording_type": "cmr"},
            ),
        )

        assert later.status_code == 201, later.text
        after = client.get(f"/api/offers/{later.json()['offer_id']}").json()["drive"]
        assert after["specifications"] == {**entered, "recording_type": "cmr"}


SEEDED_CONDITION_RULES = [
    {"pattern": r"\bmanufacturer recertified\b", "condition": "manufacturer_recertified"},
    {"pattern": r"\bseller refurbished\b", "condition": "refurbished"},
    {"pattern": r"\bopen box\b", "condition": "used"},
    {"pattern": r"\brecertified\b", "condition": "refurbished"},
    {"pattern": r"\brefurbished\b", "condition": "refurbished"},
    {"pattern": r"\brenewed\b", "condition": "refurbished"},
    {"pattern": r"\bused\b", "condition": "used"},
    {"pattern": r"\bnew\b", "condition": "new"},
]


def test_condition_rules_are_seeded_replaced_in_order_and_read_pasted_text(
    database_url: str,
) -> None:
    pasted = {"text": "Seagate Exos X18 ST18000NM000J 18TB Pre-Owned, like new\n$199.99"}
    pre_owned = {"pattern": r"\bpre-?owned\b", "condition": "used"}
    with TestClient(create_app()) as client:
        seeded = client.get("/api/condition-rules").json()
        before = client.post("/api/listing-text", json=pasted).json()["condition"]
        replaced = client.put("/api/condition-rules", json=[pre_owned, *seeded])
        after = client.post("/api/listing-text", json=pasted).json()["condition"]
        listed = client.get("/api/condition-rules").json()

    assert seeded == SEEDED_CONDITION_RULES
    assert before == "new"
    assert replaced.status_code == 200, replaced.text
    # Earlier rules win: "Pre-Owned" is read before "new".
    assert (after, listed) == ("used", [pre_owned, *SEEDED_CONDITION_RULES])


def test_a_condition_rule_that_cannot_work_is_refused_where_it_is_and_nothing_is_replaced(
    database_url: str,
) -> None:
    """Which rules cannot work is the schema's (tests/unit/catalog/test_schemas.py)."""
    rule = {"pattern": "(unclosed", "condition": "used"}
    with TestClient(create_app()) as client:
        refused = client.put("/api/condition-rules", json=[SEEDED_CONDITION_RULES[0], rule])
        kept = client.get("/api/condition-rules").json()

    assert refused.status_code == 422
    assert [issue["loc"] for issue in refused.json()["detail"]] == [["body", 1, "pattern"]]
    assert kept == SEEDED_CONDITION_RULES


def test_pasted_listing_text_is_read_into_the_fields_of_an_offer(database_url: str) -> None:
    pasted = (
        "\n  Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive  \n"
        "Was $299.99\n$1,219.99\nIn stock\n"
    )
    with TestClient(create_app()) as client:
        read = client.post("/api/listing-text", json={"text": pasted})
        nothing = client.post("/api/listing-text", json={"text": "hello"})

    assert read.status_code == 200, read.text
    assert read.json() == {
        "title": "Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive",
        "mpn": "ST18000NM000J",
        "capacity_gb": 18000,
        "condition": "refurbished",
        "brand": "Seagate",
        "item_price_cents": 121999,
    }
    assert nothing.json() == {
        "title": "hello",
        "mpn": None,
        "capacity_gb": None,
        "condition": None,
        "brand": None,
        "item_price_cents": None,
    }


def test_every_store_is_a_source_and_offers_are_recorded_under_and_named_by_one(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        by_hand = client.post("/api/sources", json={"name": "Server Orbit!", "kind": "manual"})
        unknown = post(client, "/api/prices", price_payload(store="nowhere", seller=""))
        recorded = post(client, "/api/prices", price_payload(store="serverorbit", seller=""))
        offer = saved_offer(client, recorded)
        due_now = client.get("/api/sources", params={"due": True}).json()
        no_stores = client.get("/api/stores")

    assert by_hand.status_code == 201, by_hand.text
    assert {name: by_hand.json()[name] for name in ("key", "kind", "base_url", "settings",
                                                    "next_run_at")} == {
        "key": "serverorbit", "kind": "manual", "base_url": "", "settings": {}, "next_run_at": None,
    }  # fmt: skip
    assert unknown.status_code == 422
    assert unknown.json()["detail"][0]["loc"] == ["body", "store"]
    assert (offer["store"], offer["store_name"]) == (
        "serverorbit",
        "Server Orbit!",
    )
    # A store entered by hand is never collected.
    assert "Server Orbit!" not in names(due_now)
    assert no_stores.status_code == 404


# Every database starts with the three stores the collector had built in, and Other, for
# one-off stores entered by hand under the seller's name.
COLLECTED_SOURCES = ["ServerPartDeals", "Western Digital", "goHardDrive"]
SEEDED_SOURCES = [*COLLECTED_SOURCES, "Other"]


def source_input(**fields: Any) -> dict[str, Any]:
    return {
        "name": "Server Orbit",
        "kind": "shopify",
        "settings": {
            "collections": ["hard-drives"],
            "free_shipping": False,
        },
        "base_url": "https://www.serverpartdeals.com",
        "schedule": "0 3 * * *",
        "enabled": True,
        "transport": "direct",
        "basis": "unconfirmed",
        "obey_robots": True,
        "notes": "",
        **fields,
    }


def names(sources: list[dict[str, Any]]) -> set[str]:
    return {source["name"] for source in sources}


def test_sources_are_added_listed_and_edited_with_their_next_scheduled_run(
    database_url: str,
) -> None:
    before = datetime.now(UTC)
    with TestClient(create_app()) as client:
        assert names(client.get("/api/sources").json()) == set(SEEDED_SOURCES)
        added = client.post("/api/sources", json=source_input())
        assert added.status_code == 201, added.text
        source = added.json()
        edited = client.put(
            f"/api/sources/{source['id']}",
            json=source_input(
                schedule="30 */6 * * *", enabled=False, transport="browser", basis="permission"
            ),
        )
        listed = client.get("/api/sources").json()

    assert {
        key: value for key, value in source.items() if key not in ("id", "key", "next_run_at")
    } == source_input()
    # It has never run, so it is due straight away.
    assert before <= datetime.fromisoformat(source["next_run_at"]) <= datetime.now(UTC)
    assert edited.status_code == 200, edited.text
    assert [entry for entry in listed if entry["id"] == source["id"]] == [
        {**source_input(schedule="30 */6 * * *", enabled=False, transport="browser",
                        basis="permission"),
         "id": source["id"], "key": "serverorbit", "next_run_at": None}
    ]  # fmt: skip
    assert names(listed) == {*SEEDED_SOURCES, "Server Orbit"}


def due(client: TestClient) -> set[str]:
    return names(client.get("/api/sources", params={"due": True}).json())


def report_run_of(client: TestClient, key: str, started_at: datetime) -> None:
    """A run of a source that started then and completed five minutes later."""
    run_id = str(uuid4())
    started = client.post(
        "/api/collection-runs",
        json={"id": run_id, "source": key, "started_at": started_at.isoformat()},
    )
    assert started.status_code == 201, started.text
    counts = dict.fromkeys(("seen", "recorded", "queued", "ignored", "failed"), 0)
    finished_at = (started_at + timedelta(minutes=5)).isoformat()
    ended = client.patch(
        f"/api/collection-runs/{run_id}",
        json={"status": "completed", "finished_at": finished_at, **counts},
    )
    assert ended.status_code == 200, ended.text


def test_a_source_is_due_until_it_runs_and_again_once_its_schedule_fires_after_that_run(
    database_url: str,
) -> None:
    now = datetime.now(UTC)
    with TestClient(create_app()) as client:
        source = client.post("/api/sources", json=source_input()).json()
        client.post("/api/sources", json=source_input(name="Old Run"))
        never_run = due(client)
        report_run_of(client, "serverorbit", now)
        report_run_of(client, "oldrun", now - timedelta(days=2))
        # An older run of a source that has run since does not make it due.
        report_run_of(client, "serverorbit", now - timedelta(days=2))
        after_runs = due(client)
        listed = {entry["name"]: entry for entry in client.get("/api/sources").json()}

    assert never_run == {*COLLECTED_SOURCES, "Server Orbit", "Old Run"}
    assert after_runs == {*COLLECTED_SOURCES, "Old Run"}
    next_run = datetime.fromisoformat(listed["Server Orbit"]["next_run_at"])
    assert (next_run.hour, next_run.minute) == (3, 0)
    assert now < next_run <= now + timedelta(days=1)
    # Overdue: the first 03:00 after its last run has passed.
    overdue = datetime.fromisoformat(listed["Old Run"]["next_run_at"])
    assert (overdue.hour, overdue.minute) == (3, 0)
    assert now - timedelta(days=2) < overdue <= now - timedelta(days=1)
    assert source["id"] == listed["Server Orbit"]["id"]


def test_a_switched_off_source_is_due_only_when_asked_to_run_now(database_url: str) -> None:
    with TestClient(create_app()) as client:
        source = client.post("/api/sources", json=source_input(enabled=False)).json()
        idle = due(client)
        asked = client.post(f"/api/sources/{source['id']}/run")
        queued = due(client)
        report_run_of(client, "serverorbit", datetime.now(UTC) - timedelta(hours=1))
        before_the_request = due(client)
        report_run_of(client, "serverorbit", datetime.now(UTC))
        after_the_request = due(client)
        missing = client.post(f"/api/sources/{uuid4()}/run")

    assert "Server Orbit" not in idle
    assert source["next_run_at"] is None
    assert asked.status_code == 202, asked.text
    assert asked.json()["id"] == source["id"]
    assert datetime.fromisoformat(asked.json()["next_run_at"]) <= datetime.now(UTC)
    assert "Server Orbit" in queued
    # A run that started before the request does not answer it; one that started after does.
    assert "Server Orbit" in before_the_request
    assert "Server Orbit" not in after_the_request
    assert missing.status_code == 404


def test_a_refused_source_is_refused_on_its_field_and_nothing_is_saved(
    database_url: str,
) -> None:
    """Every refusal is the schema's (tests/unit/collection/test_schemas.py); this is where the
    form is told it is, without the kind a source is checked as."""
    with TestClient(create_app()) as client:
        refused = client.post("/api/sources", json=source_input(schedule="nightly"))
        listed = client.get("/api/sources").json()

    assert refused.status_code == 422
    assert [issue["loc"] for issue in refused.json()["detail"]] == [["body", "schedule"]]
    assert names(listed) == set(SEEDED_SOURCES)


def test_source_names_and_keys_are_unique_and_only_existing_sources_can_be_edited(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        client.post("/api/sources", json=source_input())
        other = client.post("/api/sources", json=source_input(name="Elsewhere")).json()
        duplicate = client.post("/api/sources", json=source_input(schedule="0 4 * * *"))
        same_key = client.post("/api/sources", json=source_input(name="Server-Orbit"))
        renamed_onto = client.put(f"/api/sources/{other['id']}", json=source_input())
        missing = client.put(f"/api/sources/{uuid4()}", json=source_input(name="Nowhere"))

    assert [response.status_code for response in (duplicate, same_key, renamed_onto, missing)] == [
        409, 409, 409, 404,
    ]  # fmt: skip


def test_a_source_is_always_given_with_the_settings_its_kind_has_now(database_url: str) -> None:
    """A source saved before a setting existed, or with one since dropped, reads as if saved
    today, so the collector never has to guess a default."""
    saved_long_ago = {"product_path_pattern": "-p/", "title_prefix": "Old Store - "}
    with TestClient(create_app()) as client:
        source = client.post("/api/sources", json=source_input(kind="sitemap", settings={})).json()
        broken = client.post("/api/sources", json=source_input(name="No Collections")).json()
        engine = create_engine(database_url)
        with engine.begin() as connection:
            for saved, source_id in ((saved_long_ago, source["id"]), ({}, broken["id"])):
                connection.execute(
                    text("UPDATE sources SET settings = CAST(:settings AS jsonb) WHERE id = :id"),
                    {"settings": json.dumps(saved), "id": source_id},
                )
        engine.dispose()
        listed = client.get("/api/sources").json()
        due_now = client.get("/api/sources", params={"due": True}).json()

    expected = {
        "sitemap_path": "",
        "product_path_pattern": "-p/",
        "free_shipping_marker": "",
        **dict.fromkeys(
            ("data_pattern", "data_items", "data_model_field", "data_name_field",
             "data_price_field", "data_brand_field", "data_stock_field", "data_in_stock_value"),
            "",
        ),
    }  # fmt: skip
    assert [entry["settings"] for entry in listed if entry["id"] == source["id"]] == [expected]
    assert [entry["settings"] for entry in due_now if entry["id"] == source["id"]] == [expected]
    # Settings its kind would refuse now are given with its blanks filled, not checked again.
    blank = {"collections": [], "free_shipping": False}
    assert [entry["settings"] for entry in listed if entry["id"] == broken["id"]] == [blank]


def test_a_setting_that_does_not_fit_is_refused_where_the_form_shows_it(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        refused = client.post("/api/sources", json=source_input(settings={"collections": []}))

    assert refused.status_code == 422
    assert [(issue["loc"], issue["msg"]) for issue in refused.json()["detail"]] == [
        (["body", "settings", "collections"], "Enter at least one.")
    ]


def test_permission_taken_away_while_robots_txt_is_ignored_is_refused_not_undone(
    database_url: str,
) -> None:
    """Who may ignore robots.txt is the schema's (tests/unit/collection/test_schemas.py)."""
    permitted = source_input(name="DirectMacro", basis="permission", obey_robots=False)
    with TestClient(create_app()) as client:
        source_id = client.post("/api/sources", json=permitted).json()["id"]
        withdrawn = client.put(
            f"/api/sources/{source_id}", json={**permitted, "basis": "terms_allow"}
        )
        kept = [s for s in client.get("/api/sources").json() if s["id"] == source_id]
        restored = client.put(
            f"/api/sources/{source_id}",
            json={**permitted, "basis": "terms_allow", "obey_robots": True},
        )

    assert withdrawn.status_code == 422
    assert [issue["loc"] for issue in withdrawn.json()["detail"]] == [["body", "obey_robots"]]
    assert [(s["basis"], s["obey_robots"]) for s in kept] == [("permission", False)]
    assert restored.status_code == 200, restored.text
    assert (restored.json()["basis"], restored.json()["obey_robots"]) == ("terms_allow", True)


def test_a_source_with_offers_or_queued_offers_is_kept_and_so_is_other(database_url: str) -> None:
    with TestClient(create_app()) as client:
        sources = {source["key"]: source["id"] for source in client.get("/api/sources").json()}
        post(client, "/api/prices", price_payload(store="serverpartdeals", seller=""))
        post(client, "/api/prices", scraped_payload(store="goharddrive", mpn=None))
        refused = {
            key: client.delete(f"/api/sources/{sources[key]}")
            for key in ("serverpartdeals", "goharddrive", "other")
        }
        listed = client.get("/api/sources").json()

    assert {key: answer.status_code for key, answer in refused.items()} == {
        "serverpartdeals": 409,
        "goharddrive": 409,
        "other": 409,
    }
    assert refused["serverpartdeals"].json() == {
        "detail": "Offers are recorded under this source. Switch it off instead."
    }
    assert refused["other"].json() == {"detail": "Other is always kept, for one-off stores."}
    assert names(listed) == set(SEEDED_SOURCES)


def test_a_source_keeps_the_key_it_was_created_with_when_renamed(database_url: str) -> None:
    with TestClient(create_app()) as client:
        source = client.post("/api/sources", json=source_input()).json()
        renamed = client.put(
            f"/api/sources/{source['id']}", json=source_input(name="Orbit Refurbished")
        ).json()

    assert (renamed["name"], renamed["key"]) == ("Orbit Refurbished", "serverorbit")


def test_the_kinds_of_store_are_given_as_their_settings_describe_them(database_url: str) -> None:
    """The Admin form is drawn from this; how each kind is described is its settings model's
    (tests/unit/collection/test_schemas.py)."""
    with TestClient(create_app()) as client:
        kinds = {kind["kind"]: kind for kind in client.get("/api/source-kinds").json()}

    assert sorted(kinds) == ["manual", "sap_commerce", "shopify", "sitemap"]
    assert kinds["manual"] == {
        "kind": "manual",
        "label": "Entered by hand",
        "collected": False,
        "page_test": False,
        "groups": [],
        "settings": [],
    }
    assert [setting["name"] for setting in kinds["shopify"]["settings"]] == [
        "collections",
        "free_shipping",
    ]


def test_the_published_contract_types_each_kind_of_stores_settings(database_url: str) -> None:
    """The collector's client is generated from the contract, so it reads a store's settings as
    the fields of its kind, not as a dictionary to pick through."""
    with TestClient(create_app()) as client:
        spec = client.get("/openapi.json").json()

    sent = spec["paths"]["/api/sources"]["post"]["requestBody"]["content"]["application/json"]
    read = response_schema(spec, "/api/sources", "get", "200")
    for sources in (schema_of(spec, sent["schema"]), read):
        assert sources["discriminator"]["propertyName"] == "kind"
        kinds = sources["discriminator"]["mapping"]
        assert sorted(kinds) == ["manual", "sap_commerce", "shopify", "sitemap"]
        shopify = schema_of(spec, {"$ref": kinds["shopify"]})
        settings = schema_of(spec, shopify["properties"]["settings"])
        assert settings["properties"]["collections"]["type"] == "array"
        assert settings["properties"]["collections"]["items"] == {"type": "string"}
        assert settings["properties"]["free_shipping"]["type"] == "boolean"
        assert settings["additionalProperties"] is False


def test_a_kind_of_store_nobody_reads_is_refused(database_url: str) -> None:
    with TestClient(create_app()) as client:
        refused = client.post("/api/sources", json=source_input(kind="magento"))

    assert refused.status_code == 422
    assert refused.json()["detail"][0]["loc"] == ["body", "kind"]


def priced_days_ago(client: TestClient, now: datetime) -> Any:
    """Record an item price for a drive at one store as it stood so many days before now. Each is
    a 10 TB drive with shipping to pay, so a cent of item price is a tenth of a cent per terabyte."""

    def record(mpn: str, item: int, days: float, **fields: Any) -> None:
        payload = price_payload(
            mpn=mpn,
            store="serverpartdeals",
            seller="",
            condition="new",
            capacity_gb=10000,
            item_price_cents=item,
            shipping_cents=500,
            observed_at=(now - timedelta(days=days)).isoformat(),
        )
        response = post(client, "/api/prices", {**payload, **fields})
        assert response.status_code == 201, response.text

    return record


def test_trends_follow_the_typical_item_price_per_terabyte_of_drives_priced_all_period(
    database_url: str,
) -> None:
    now = datetime.now(UTC)
    with TestClient(create_app()) as client:
        record = priced_days_ago(client, now)
        record("ST10000NM001G", 10000, 40.5)
        record("ST10000NM002G", 20000, 40.5)
        record("ST10000NM003G", 30000, 40.5)
        # Ten days ago the middle drive drops from $20 to $16 a terabyte.
        record("ST10000NM002G", 16000, 10.5)
        # A drive first priced five days ago is not counted: it would move the line by arriving.
        record("ST10000NM004G", 1000, 5.5)
        # Every offer was checked just now, so each price still stands.
        for mpn, item in [("ST10000NM001G", 10000), ("ST10000NM002G", 16000)]:
            record(mpn, item, 0.001)
        record("ST10000NM003G", 30000, 0.001)
        record("ST10000NM004G", 1000, 0.001)

        response = client.get("/api/trends", params={"days": 30})

    assert response.status_code == 200, response.text
    trends = response.json()
    assert (trends["days"], trends["by"], trends["parts"]) == (30, None, [])
    market = trends["market"]
    assert (market["counted"], market["of"]) == (3, 4)
    points = {point["days_ago"]: point for point in market["points"]}
    assert sorted(points) == list(range(31))
    # Cents per terabyte: the median drive, and the middle half around it. Shipping is left out.
    assert points[30] == {"days_ago": 30, "median": 2000, "low": 1500, "high": 2500}
    assert points[11] == {"days_ago": 11, "median": 2000, "low": 1500, "high": 2500}
    assert points[10] == {"days_ago": 10, "median": 1600, "low": 1300, "high": 2300}
    assert points[0] == {"days_ago": 0, "median": 1600, "low": 1300, "high": 2300}


def test_trends_split_the_market_when_asked_and_refuse_a_period_or_split_there_is_not(
    database_url: str,
) -> None:
    now = datetime.now(UTC)
    with TestClient(create_app()) as client:
        record = priced_days_ago(client, now)
        record("ST10000NM001G", 10000, 40.5)
        record("ST18000NM000J", 36000, 40.5, capacity_gb=18000)
        # Last checked ten days ago: within the fortnight asked for below, not within a week.
        record("ST10000NM001G", 10000, 10.5)
        record("ST18000NM000J", 36000, 0.001, capacity_gb=18000)

        split = {"days": 30, "by": "capacity"}
        by_capacity = client.get("/api/trends", params={**split, "recent_days": 14})
        strict = client.get("/api/trends", params=split)
        # Ninety days unless told otherwise.
        assert client.get("/api/trends").json()["days"] == 90
        assert client.get("/api/trends", params={"days": 45}).status_code == 422
        assert client.get("/api/trends", params={"by": "brand"}).status_code == 422
        assert client.get("/api/trends", params={"recent_days": 0}).status_code == 422

    assert by_capacity.status_code == 200, by_capacity.text
    trends = by_capacity.json()
    assert (trends["days"], trends["by"]) == (30, "capacity")
    assert [part["key"] for part in trends["parts"]] == ["10000", "18000"]
    small, large = (part["series"] for part in trends["parts"])
    assert small["points"][-1] == {"days_ago": 0, "median": 1000, "low": 1000, "high": 1000}
    assert large["points"][-1] == {"days_ago": 0, "median": 2000, "low": 2000, "high": 2000}
    # Left to the usual week, the offer unchecked for ten days ended at its last check.
    assert [point["days_ago"] for point in strict.json()["parts"][0]["series"]["points"]] == list(
        range(30, 10, -1)
    )


def test_a_trend_can_look_back_a_week_or_a_fortnight_and_says_how_far_back_prices_go(
    database_url: str,
) -> None:
    """Prices have been collected for ten days: a fortnight is too long to follow any drive
    over, a week is not."""
    now = datetime.now(UTC)
    with TestClient(create_app()) as client:
        record = priced_days_ago(client, now)
        first = now - timedelta(days=10)
        record("ST10000NM001G", 10000, 10)
        record("ST10000NM001G", 10000, 0.001)
        week = client.get("/api/trends", params={"days": 7}).json()
        fortnight = client.get("/api/trends", params={"days": 14}).json()

    assert (week["days"], week["market"]["counted"]) == (7, 1)
    assert (fortnight["days"], fortnight["market"]["counted"]) == (14, 0)
    for trend in (week, fortnight):
        since = datetime.fromisoformat(trend["since"])
        assert abs(since - first) < timedelta(minutes=1)


def followed_drives(client: TestClient, now: datetime) -> Any:
    """Three drives priced all month, each checked just now. Returns the recorder for more."""
    record = priced_days_ago(client, now)
    for mpn, item in [("ST10000NM001G", 10000), ("ST10000NM002G", 20000), ("ST10000NM003G", 30000)]:
        record(mpn, item, 40.5)
        record(mpn, item, 0.001)
    return record


def test_a_trend_and_todays_prices_follow_only_the_drives_the_prices_page_would_show(
    database_url: str,
) -> None:
    """Narrowed by the same filters as the drives listed, each narrowing kept apart from the
    rest, so are the drives being considered getting cheaper is answered for them alone."""
    with TestClient(create_app()) as client:
        record = followed_drives(client, datetime.now(UTC))
        for days in (40.5, 0.001):
            record("ST18000NM000J", 36000, days, capacity_gb=18000)
        every = client.get("/api/trends", params={"days": 30}).json()
        large = client.get("/api/trends", params={"days": 30, "capacity": 18000}).json()
        searched = client.get("/api/trends", params={"days": 30, "q": "ST10000NM00"}).json()
        again = client.get("/api/trends", params={"days": 30}).json()
        today = client.get("/api/reports/prices-today", params={"capacity": 18000}).json()
        refused = client.get("/api/trends", params={"days": 30, "limit": 5})

    assert (every["market"]["counted"], large["market"]["counted"]) == (4, 1)
    assert large["market"]["points"][-1]["median"] == 2000
    assert searched["market"]["counted"] == 3
    assert again == every
    assert [mark["capacity_gb"] for mark in today] == [18000]
    # Paging and order are the list's own.
    assert refused.status_code == 422


def test_trends_are_kept_once_worked_out_and_answered_from_what_was_kept(database_url: str) -> None:
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        followed_drives(client, datetime.now(UTC))
        first = client.get("/api/trends", params={"days": 30}).json()
        assert first["market"]["counted"] == 3
        with engine.begin() as connection:
            kept = connection.execute(text("SELECT days, by, recent_days FROM trends")).all()
            # Nothing but the kept answer says 99, so answering 99 is answering from it.
            connection.execute(
                text("UPDATE trends SET body = jsonb_set(body, '{market,counted}', '99')")
            )
        again = client.get("/api/trends", params={"days": 30}).json()
        client.get("/api/trends", params={"days": 30, "by": "capacity"})
        client.get("/api/trends", params={"days": 30, "recent_days": 14})
        with engine.connect() as connection:
            answers = connection.execute(text("SELECT count(*) FROM trends")).scalar_one()
    engine.dispose()

    assert kept == [(30, "", 7)]
    assert again == {**first, "market": {**first["market"], "counted": 99}}
    # One answer for each period, split and allowance asked for.
    assert answers == 3


def test_a_price_recorded_for_an_earlier_day_changes_that_day_of_a_kept_trend(
    database_url: str,
) -> None:
    """Prices can be entered backdated: one recorded now for ten days ago changes the trend from
    ten days ago on, though it was kept before."""
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        record = followed_drives(client, datetime.now(UTC))
        client.get("/api/trends", params={"days": 30})
        # The cheapest drive, at half its price ten days ago.
        record("ST10000NM001G", 5000, 10)
        kept = client.get("/api/trends", params={"days": 30}).json()
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM trends"))
        afresh = client.get("/api/trends", params={"days": 30}).json()
    engine.dispose()

    assert kept == afresh
    assert [point["low"] for point in afresh["market"]["points"] if point["days_ago"] == 9] != [
        1500
    ]


def test_a_price_recorded_since_a_trend_was_kept_has_it_worked_out_again(
    database_url: str,
) -> None:
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        record = followed_drives(client, datetime.now(UTC))
        first = client.get("/api/trends", params={"days": 30}).json()
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE trends SET body = jsonb_set(body, '{market,counted}', '99')")
            )
        # The middle drive drops from $20 to $16 a terabyte, and a drive is priced for the first time.
        record("ST10000NM002G", 16000, 0)
        record("ST10000NM004G", 1000, 0)
        after = client.get("/api/trends", params={"days": 30}).json()
    engine.dispose()

    assert first["market"]["points"][-1] == {
        "days_ago": 0,
        "median": 2000,
        "low": 1500,
        "high": 2500,
    }
    # Today is read again from the prices as they now stand, over the drives followed all period.
    assert after["market"]["points"][-1] == {
        "days_ago": 0,
        "median": 1600,
        "low": 1300,
        "high": 2300,
    }
    assert after["market"]["points"][:-1] == first["market"]["points"][:-1]
    # Worked out again, all of it: not the answer that was kept. The new drive was not priced
    # as the period opened, so it is not followed.
    assert (after["market"]["counted"], after["market"]["of"]) == (3, 4)


def test_a_trend_kept_on_an_earlier_day_is_worked_out_afresh_and_kept_again(
    database_url: str,
) -> None:
    """When a kept trend is answered is the service's (tests/unit/reporting/test_service.py);
    this is the day it was kept on, as the database has it."""
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        followed_drives(client, datetime.now(UTC))
        first = client.get("/api/trends", params={"days": 30}).json()
        with engine.begin() as connection:
            # As if it had been worked out yesterday; 99 is what only the kept answer says.
            connection.execute(
                text(
                    "UPDATE trends SET as_of = as_of - interval '1 day', "
                    "body = jsonb_set(body, '{market,counted}', '99')"
                )
            )
        after = client.get("/api/trends", params={"days": 30}).json()
        with engine.connect() as connection:
            kept_on = connection.execute(text("SELECT as_of::date FROM trends")).scalar_one()
    engine.dispose()

    assert after == first
    assert kept_on == datetime.now(UTC).date()


def collected_payload(**fields: Any) -> dict[str, Any]:
    """A price as a collector submits it: under the store it read, and to be queued for review
    when it cannot be matched."""
    return scraped_payload(**fields)


def test_a_price_is_answered_with_what_was_done_and_the_ids_of_what_it_touched(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        first = post(client, "/api/prices", price_payload())
        [offer] = with_history(client)
        again = post(client, "/api/prices", price_payload(observed_at="2026-09-22T12:00:00Z"))

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
        collected = post(client, "/api/prices", collected_payload())
        manual = post(client, "/api/prices", price_payload(store="serverpartdeals", seller="x"))
        by_seller = {offer["seller"]: offer for offer in client.get("/api/offers").json()}

    assert (collected.status_code, manual.status_code) == (201, 201)
    # Both are under the same store: who submitted a price is kept apart from where it was seen.
    assert {offer["store"] for offer in by_seller.values()} == {"serverpartdeals"}
    assert by_seller[""]["latest"]["provenance"] == "collected"
    assert by_seller["x"]["latest"]["provenance"] == "manual"


def test_a_price_that_cannot_be_matched_is_refused_unless_review_is_asked_for(
    database_url: str,
) -> None:
    unknown_drive = {"mpn": "ST20000NM007D", "capacity_gb": None}
    with TestClient(create_app()) as client:
        no_capacity = post(client, "/api/prices", price_payload(**unknown_drive))
        queue_before = client.get("/api/review-items").json()
        queued = post(client, "/api/prices", price_payload(**unknown_drive, on_unmatched="queue"))
        [waiting] = client.get("/api/review-items").json()
        offers = client.get("/api/offers").json()

    assert (no_capacity.status_code, no_capacity.json()["detail"][0]["loc"]) == (
        422,
        ["body", "capacity_gb"],
    )
    assert queue_before == []
    assert (queued.status_code, queued.json()) == (
        202,
        {"status": "queued", "offer_id": None, "price_id": None, "review_item_id": waiting["id"]},
    )
    assert (waiting["store"], waiting["reason"]) == ("other", "missing_capacity")
    assert offers == []


def test_a_price_can_name_the_offer_it_is_for_instead_of_describing_it(database_url: str) -> None:
    check = {"item_price_cents": 17900, "observed_at": "2026-09-22T12:00:00Z"}
    with TestClient(create_app()) as client:
        offer_id = post(client, "/api/prices", price_payload()).json()["offer_id"]
        named = post(client, "/api/prices", {"offer_id": offer_id, **check})
        [offer] = with_history(client)
        missing = post(client, "/api/prices", {"offer_id": str(uuid4()), **check})

    assert named.status_code == 201, named.text
    assert named.json()["offer_id"] == offer_id == offer["id"]
    assert [price["item_price_cents"] for price in offer["observations"]] == [18900, 17900]
    # Shipping stays what the entry says, as for any price: free unless given.
    assert offer["latest"]["shipping_cents"] == 0
    assert (missing.status_code, missing.json()["detail"]) == (404, "Offer not found")


def test_a_retry_replays_whatever_was_done_whether_recorded_queued_or_ignored(
    database_url: str,
) -> None:
    unmatched = collected_payload(mpn=None)
    sold_out = collected_payload(in_stock=False, seller="never seen")
    with TestClient(create_app()) as client:
        answers = []
        for payload in (collected_payload(), unmatched, sold_out):
            key = str(uuid4())
            first, retry = (post(client, "/api/prices", payload, key) for _ in range(2))
            changed = post(client, "/api/prices", {**payload, "item_price_cents": 1}, key)
            answers.append((first.status_code, first.json()["status"], retry.status_code))
            assert retry.json() == first.json()
            assert changed.status_code == 409
        queue = client.get("/api/review-items").json()
        [offer] = with_history(client)

    assert answers == [(201, "recorded", 201), (202, "queued", 202), (200, "ignored", 200)]
    assert len(queue) == 1
    assert len(offer["observations"]) == 1


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
        post(client, "/api/prices", collected_payload(mpn=None))
        failed = post(client, "/api/prices", payload, key)
        offers = client.get("/api/offers").json()
        queue = client.get("/api/review-items").json()
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(text("DROP TRIGGER refuse ON mpn_aliases"))
            drives = connection.execute(text("SELECT count(*) FROM drives")).scalar_one()
        engine.dispose()
        retried = post(client, "/api/prices", payload, key)

    assert failed.status_code == 500
    # No offer, no drive, and the offer still waits for review as it did before.
    assert (offers, drives, len(queue)) == ([], 0, 1)
    # The save key was not spent on the failure: the retry does the work.
    assert (retried.status_code, retried.json()["status"]) == (201, "recorded")


def test_a_manual_price_queued_for_review_is_recorded_as_manual_when_resolved(
    database_url: str,
) -> None:
    """Who submitted a price and what happens when it cannot be matched are separate choices."""
    payload = price_payload(mpn=None, condition=None, on_unmatched="queue")
    with TestClient(create_app()) as client:
        queued = post(client, "/api/prices", payload)
        assert (queued.status_code, queued.json()["status"]) == (202, "queued")
        waiting = client.get("/api/review-items").json()
        resolved = client.put(
            f"/api/review-items/{queued.json()['review_item_id']}/decision",
            json={"decision": "match", "mpn": "ST18000NM000J", "condition": "new"},
        )
        collected = post(client, "/api/prices", scraped_payload(mpn=None, condition=None)).json()
        waiting_collected = client.get("/api/review-items").json()
        recorded = client.get(f"/api/offers/{resolved.json()['offer_id']}").json()
    assert [item["provenance"] for item in waiting] == ["manual"]
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "matched"
    assert recorded["latest"]["provenance"] == "manual"
    assert (collected["status"], [item["provenance"] for item in waiting_collected]) == (
        "queued",
        ["collected"],
    )


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
        retried = post(client, "/api/prices", price_payload(), key=key)
        again = post(client, "/api/prices", price_payload(), key=key)
        offers = client.get("/api/offers").json()
    engine.dispose()
    assert (retried.status_code, again.status_code) == (409, 409)
    assert retried.json() == {
        "detail": "This save key was used before prices were recorded this way, so this request"
        " cannot be matched to the one it answered. Nothing was saved: check whether the price"
        " is already recorded, then save it under a new key."
    }
    assert offers == []


MATCH = {
    "decision": "match",
    "mpn": "ST18000NM000J",
    "condition": "manufacturer_recertified",
    "capacity_gb": 18000,
}


def queued_item(client: TestClient, **fields: Any) -> str:
    queued = post(client, "/api/prices", scraped_payload(mpn=None, condition=None, **fields))
    assert queued.status_code == 202, queued.text
    item_id: str = queued.json()["review_item_id"]
    return item_id


def test_a_review_decision_is_answered_again_when_repeated_without_doing_it_twice(
    database_url: str,
) -> None:
    """A decision whose answer was lost can be sent again: the same decision gets the first answer
    and records nothing more, while a different one is refused."""
    with TestClient(create_app()) as client:
        item_id = queued_item(client)
        decided = client.put(f"/api/review-items/{item_id}/decision", json=MATCH)
        waiting = client.get("/api/review-items").json()
        repeated = client.put(
            f"/api/review-items/{item_id}/decision", json={**MATCH, "mpn": "st18000nm000j"}
        )
        changed = client.put(f"/api/review-items/{item_id}/decision", json={"decision": "ignore"})
        offer = client.get(f"/api/offers/{decided.json()['offer_id']}").json()
    assert decided.status_code == 200, decided.text
    assert decided.json() == {"status": "matched", "offer_id": offer["id"]}
    assert waiting == []
    assert (repeated.status_code, repeated.json()) == (200, decided.json())
    assert changed.status_code == 409, changed.text
    assert [price["item_price_cents"] for price in offer["observations"]] == [36999]
    assert (offer["mpn"], offer["condition"]) == ("ST18000NM000J", "manufacturer_recertified")


def test_an_ignore_decision_names_no_offer_and_is_answered_again_when_repeated(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        item_id = queued_item(client)
        ignored = client.put(f"/api/review-items/{item_id}/decision", json={"decision": "ignore"})
        repeated = client.put(f"/api/review-items/{item_id}/decision", json={"decision": "ignore"})
        changed = client.put(f"/api/review-items/{item_id}/decision", json=MATCH)
        offers = client.get("/api/offers").json()
    assert (ignored.status_code, ignored.json()) == (200, {"status": "ignored", "offer_id": None})
    assert (repeated.status_code, repeated.json()) == (200, ignored.json())
    assert changed.status_code == 409, changed.text
    assert offers == []


def test_a_review_decision_must_say_what_it_decides_and_nothing_else(database_url: str) -> None:
    with TestClient(create_app()) as client:
        item_id = queued_item(client)
        # What a decision may say is the schema's (tests/unit/catalog/test_schemas.py).
        unclear = client.put(f"/api/review-items/{item_id}/decision", json={"decision": "keep"})
        unknown = client.put(f"/api/review-items/{uuid4()}/decision", json=MATCH)
        still_waiting = [item["id"] for item in client.get("/api/review-items").json()]
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
        failed = client.put(f"/api/review-items/{item_id}/decision", json=MATCH)
        offers = client.get("/api/offers").json()
        with engine.begin() as connection:
            connection.execute(text("DROP TRIGGER refuse ON scraped_matches"))
        retried = client.put(f"/api/review-items/{item_id}/decision", json=MATCH)
    engine.dispose()
    assert (failed.status_code, offers) == (500, [])
    assert (retried.status_code, retried.json()["status"]) == (200, "matched")


def test_the_review_queue_names_the_store_each_offer_was_seen_at(database_url: str) -> None:
    with TestClient(create_app()) as client:
        queued_item(client)
        queued_item(client, store="goharddrive", url="https://www.goharddrive.com/p/1")
        everything = client.get("/api/review-items").json()
        one_store = client.get("/api/review-items", params={"store": "goharddrive"})
    assert {item["store"] for item in everything} == {"serverpartdeals", "goharddrive"}
    assert [item["store"] for item in one_store.json()] == ["goharddrive"]
    assert one_store.headers["X-Total-Count"] == "1"


def test_a_drive_is_corrected_a_field_at_a_time(database_url: str) -> None:
    """What a correction leaves out stays as it was, down to each specification."""
    with TestClient(create_app()) as client:
        recorded = post(
            client,
            "/api/prices",
            scraped_payload(
                brand="Seagate",
                specifications={"media_type": "hdd", "interface": "sas", "intended_use": ["nas"]},
            ),
        )
        drive = saved_offer(client, recorded)["drive"]
        path = f"/api/drives/{drive['id']}"
        interface = client.patch(path, json={"specifications": {"interface": "sata"}})
        capacity = client.patch(path, json={"capacity_gb": 20000})
        nothing = client.patch(path, json={})
        unbranded = client.patch(path, json={"brand": None})
        # What a correction cannot clear is the schema's (tests/unit/catalog/test_schemas.py).
        refused = client.patch(path, json={"capacity_gb": None})
        unknown = client.patch(f"/api/drives/{uuid4()}", json={"capacity_gb": 20000})
        final = client.get("/api/offers").json()[0]["drive"]
    assert interface.status_code == 200, interface.text
    assert interface.json()["specifications"] == {
        "media_type": "hdd",
        "form_factor": "unknown",
        "interface": "sata",
        "recording_type": "unknown",
        "intended_use": ["nas"],
    }
    assert interface.json()["capacity_gb"] == 18000
    assert (capacity.status_code, capacity.json()["capacity_gb"]) == (200, 20000)
    assert capacity.json()["specifications"] == interface.json()["specifications"]
    assert (nothing.status_code, nothing.json()) == (200, capacity.json())
    assert (unbranded.status_code, unbranded.json()["brand"]) == (200, None)
    assert refused.status_code == 422
    assert unknown.status_code == 404
    assert final == unbranded.json()


def kept_trend_poisoned(engine: Any) -> None:
    """Mark every kept trend, so that an answer carrying the mark was read from what was kept."""
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE trends SET body = jsonb_set(body, '{market,counted}', '99')")
        )


def test_a_kept_trend_is_worked_out_again_once_a_drive_or_what_it_is_changes(
    database_url: str,
) -> None:
    """Trends group offers by drive and divide by its capacity, so correcting either changes
    them, though no price changed."""
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        record = followed_drives(client, datetime.now(UTC))
        for days in (40.5, 0.001):
            record("ST10000NM004G", 40000, days, store="goharddrive")
        first = client.get("/api/trends", params={"days": 30}).json()
        drives = {o["mpn"]: o["drive"]["id"] for o in client.get("/api/offers").json()}

        kept_trend_poisoned(engine)
        resized = client.patch(f"/api/drives/{drives['ST10000NM001G']}", json={"capacity_gb": 5000})
        after_capacity = client.get("/api/trends", params={"days": 30}).json()

        kept_trend_poisoned(engine)
        # Its only offer is at a store the drive it joins has none at, so the offer moves whole.
        merged = client.post(
            f"/api/drives/{drives['ST10000NM003G']}/aliases", json={"mpn": "ST10000NM004G"}
        )
        after_merge = client.get("/api/trends", params={"days": 30}).json()

        kept_trend_poisoned(engine)
        # Without its price from before the period opened, a drive was not priced all period.
        offer = next(o for o in with_history(client) if o["mpn"] == "ST10000NM002G")
        deleted = client.delete(f"/api/prices/{offer['observations'][0]['id']}")
        after_deletion = client.get("/api/trends", params={"days": 30}).json()
    engine.dispose()
    assert (resized.status_code, merged.status_code) == (200, 201)
    assert first["market"]["counted"] == 4
    assert after_capacity["market"]["counted"] == 4
    assert after_capacity["market"]["points"] != first["market"]["points"]
    # Two offers of one drive in one condition are one item, counted once.
    assert after_merge["market"]["counted"] == 3
    assert (deleted.status_code, after_deletion["market"]["counted"]) == (204, 2)
