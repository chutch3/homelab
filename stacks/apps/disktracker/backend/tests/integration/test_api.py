import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from disktracker.web import create_app


def post(
    client: TestClient, path: str, payload: dict[str, Any], key: str | None = None
) -> Response:
    return client.post(path, json=payload, headers={"Idempotency-Key": key or str(uuid4())})


def with_history(client: TestClient) -> list[dict[str, Any]]:
    """Every offer with its full price history, fetched the way the app does."""
    ids = [offer["id"] for offer in client.get("/api/listings").json()]
    return client.get("/api/price-history", params={"listing": ids}).json()


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
    with TestClient(create_app(database_url)) as client:
        direct = post(client, "/api/prices", price_payload(store="serverpartdeals", seller=""))
        assert direct.status_code == 201, direct.text
        assert (direct.json()["store"], direct.json()["seller"]) == ("serverpartdeals", "")
        again = post(
            client,
            "/api/prices",
            price_payload(store="serverpartdeals", seller="  ", observed_at="2026-09-22T12:00:00Z"),
        ).json()
        assert again["id"] == direct.json()["id"]
        beach_audio = post(client, "/api/prices", price_payload(seller="Beach Audio")).json()
        drivedeals = post(client, "/api/prices", price_payload(seller="drivedeals")).json()
        assert len({direct.json()["id"], beach_audio["id"], drivedeals["id"]}) == 3
        assert post(client, "/api/prices", price_payload(store="frys")).status_code == 422
        assert post(client, "/api/prices", price_payload(store="newegg")).status_code == 422
        unnamed = post(client, "/api/prices", price_payload(store="other", seller=""))
        assert unnamed.status_code == 422
        assert unnamed.json()["detail"][0]["loc"] == ["body", "seller"]
        named = post(client, "/api/prices", price_payload(store="other", seller="Local shop"))
        assert named.status_code == 201, named.text


def insert_legacy_listing(
    connection: Connection,
    *,
    seller: str,
    mpn: str,
    price: int,
    observed_at: str,
    condition: str = "refurbished",
) -> None:
    listing_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO listings (id, title, mpn, seller, capacity_tb, condition)"
            " VALUES (:id, 'Exos X18', :mpn, :seller, 18, :condition)"
        ),
        {"id": listing_id, "mpn": mpn, "seller": seller, "condition": condition},
    )
    connection.execute(
        text(
            "INSERT INTO observations (id, listing_id, item_price_cents, shipping_cents,"
            " fee_cents, availability, observed_at, entered_at, notes)"
            " VALUES (:id, :listing_id, :price, 0, 0, 'in_stock', :at, :at, '')"
        ),
        {"id": uuid4(), "listing_id": listing_id, "price": price, "at": observed_at},
    )


def test_migration_splits_free_text_sellers_into_stores_and_merges_spelling_variants(
    database_url: str,
) -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.attributes["database_url"] = database_url
    command.downgrade(config, "0008")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        for seller, mpn, price, day in [
            ("ServerPartDeals", "ST18000NM000J", 18000, 1),
            ("serverpartdeals", "ST18000NM000J", 17000, 2),
            ("eBay - Beach Audio", "ST18000NM000J", 88000, 1),
            ("Newegg - E.O.L. Tech Inc.", "ST18000NM000J", 53000, 1),
            ("Micro Center", "ST18000NM000J", 30000, 1),
            ("Local shop", None, 20000, 1),
        ]:
            insert_legacy_listing(
                connection,
                seller=seller,
                mpn=mpn,
                price=price,
                observed_at=f"2026-09-0{day}T12:00:00Z",
            )
    engine.dispose()
    command.upgrade(config, "head")
    with TestClient(create_app(database_url)) as client:
        offers = with_history(client)
    by_identity = {(o["store"], o["seller"]): o for o in offers}
    assert set(by_identity) == {
        ("serverpartdeals", ""),
        # Stores disktracker has no collector for become Other, named after the store.
        ("other", "eBay · Beach Audio"),
        ("other", "Newegg · E.O.L. Tech Inc."),
        ("other", "Micro Center"),
        ("other", "Local shop"),
    }
    merged = by_identity[("serverpartdeals", "")]["observations"]
    assert [o["item_price_cents"] for o in merged] == [18000, 17000]
    unconfirmed = by_identity[("other", "Local shop")]
    assert unconfirmed["mpn"].startswith("UNCONFIRMED-")
    assert unconfirmed["drive"]["mpn"] == unconfirmed["mpn"]


def test_offer_and_later_price_survive_a_new_application_instance(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        started = datetime.now(UTC)
        result = post(client, "/api/prices", price_payload())
        assert result.status_code == 201, result.text
        offer = result.json()
        assert str(UUID(offer["id"])) == offer["id"]
        assert offer["title"] == "Seagate Exos X18"
        assert offer["capacity_gb"] == 18000
        assert offer["latest"]["total_cents"] == 19900
        assert offer["latest"]["price_per_tb"] == "11.06"
        initial = offer["observations"][0]
        assert initial["observed_at"] == "2026-09-21T12:00:00Z"
        assert initial["acquisition_method"] == "manual"
        assert started <= datetime.fromisoformat(initial["entered_at"]) <= datetime.now(UTC)
        later = post(
            client,
            "/api/prices",
            price_payload(item_price_cents=17900, observed_at="2026-09-22T12:00:00Z"),
        )
        assert later.status_code == 201, later.text

    with TestClient(create_app(database_url)) as restarted:
        saved = restarted.get(f"/api/listings/{offer['id']}").json()
        assert saved["latest"]["total_cents"] == 18900
        assert [o["item_price_cents"] for o in saved["observations"]] == [18900, 17900]
        assert saved["observations"][0] == initial
        assert with_history(restarted) == [saved]


def test_offers_carry_no_correction_archive_or_revision_state(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        offer = post(client, "/api/prices", price_payload()).json()
        assert not {"corrections", "revision", "archived_at", "duplicate_of"} & set(offer)
        assert not {"corrections", "revision"} & set(offer["drive"])
        listing, observation = offer["id"], offer["latest"]["id"]
        assert post(client, "/api/listings", {}).status_code == 405
        for path in [
            f"/api/listings/{listing}/observations",
            f"/api/listings/{listing}/corrections",
            f"/api/listings/{listing}/observations/{observation}/corrections",
            f"/api/listings/{listing}/archive",
            f"/api/drives/{offer['drive']['id']}/corrections",
        ]:
            assert post(client, path, {}).status_code == 404, path


def test_retries_replay_the_original_result_and_reject_changed_payload(database_url: str) -> None:
    key = str(uuid4())
    with TestClient(create_app(database_url)) as client:
        first = post(client, "/api/prices", price_payload(), key)
        retry = post(client, "/api/prices", price_payload(), key)
        assert retry.status_code == 201
        assert retry.json() == first.json()
        assert len(with_history(client)[0]["observations"]) == 1
        changed = post(client, "/api/prices", price_payload(item_price_cents=1), key)
        assert changed.status_code == 409


def test_concurrent_retries_record_one_price(database_url: str) -> None:
    key = str(uuid4())
    with TestClient(create_app(database_url)) as client:

        def submit() -> dict[str, Any]:
            response = post(client, "/api/prices", price_payload(), key)
            assert response.status_code == 201
            return response.json()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first, second = list(executor.map(lambda _: submit(), range(2)))
        assert first == second
        assert len(with_history(client)[0]["observations"]) == 1


def test_backdated_prices_preserve_the_latest_observation(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        post(client, "/api/prices", price_payload())
        older = post(
            client,
            "/api/prices",
            price_payload(item_price_cents=10000, observed_at="2026-09-20T12:00:00Z"),
        ).json()
        assert older["latest"]["item_price_cents"] == 18900
        assert [o["item_price_cents"] for o in older["observations"]] == [10000, 18900]


def test_a_price_needs_an_item_price_and_shipping_and_fees_default_to_zero(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        started = datetime.now(UTC)
        minimal = price_payload()
        for field in ("shipping_cents", "observed_at", "notes"):
            del minimal[field]
        saved = post(client, "/api/prices", minimal)
        assert saved.status_code == 201, saved.text
        latest = saved.json()["latest"]
        assert latest["shipping_cents"] == 0
        assert latest["total_cents"] == 18900
        assert latest["price_per_tb"] == "10.50"
        assert started <= datetime.fromisoformat(latest["observed_at"]) <= datetime.now(UTC)
        assert not {"fee_cents", "availability"} & set(latest)
        no_item = price_payload()
        del no_item["item_price_cents"]
        assert post(client, "/api/prices", no_item).status_code == 422
        for rejected in (
            {"item_price_cents": None},
            {"fee_cents": 0},
            {"availability": "in_stock"},
        ):
            assert post(client, "/api/prices", price_payload(**rejected)).status_code == 422
        assert len(with_history(client)[0]["observations"]) == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mpn", ""),
        ("title", "   "),
        ("capacity_gb", 0),
        ("capacity_gb", 18000.5),
        ("capacity_gb", "18 TB"),
        ("condition", "excellent"),
        ("url", "javascript:alert(1)"),
        ("shipping_cents", -1),
        ("item_price_cents", 1.5),
        ("observed_at", "2026-09-21T12:00:00"),
    ],
)
def test_invalid_price_is_rejected_without_partial_save(
    database_url: str, field: str, value: object
) -> None:
    with TestClient(create_app(database_url)) as client:
        result = post(client, "/api/prices", price_payload(**{field: value}))
        assert result.status_code == 422
        assert result.json()["detail"][0]["loc"] == ["body", field]
        assert client.get("/api/listings").json() == []


def test_missing_offer_returns_404(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        assert client.get(f"/api/listings/{uuid4()}").status_code == 404


def test_recording_a_price_keeps_one_offer_per_store_mpn_and_condition(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
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
        assert later.status_code == 201, later.text
        offer = later.json()
        assert offer["id"] == first.json()["id"]
        assert offer["url"] == "https://example.com/disk"
        assert [o["item_price_cents"] for o in offer["observations"]] == [18900, 17900]
        other_condition = post(client, "/api/prices", price_payload(condition="new"))
        other_seller = post(client, "/api/prices", price_payload(seller="Other seller"))
        ids = {offer["id"], other_condition.json()["id"], other_seller.json()["id"]}
        assert len(ids) == 3
        assert other_seller.json()["drive"]["id"] == offer["drive"]["id"]
        assert len(client.get("/api/listings").json()) == 3


@pytest.mark.parametrize("condition", ["open_box", "seller_refurbished", "unknown"])
def test_only_the_four_normalized_conditions_are_accepted(
    database_url: str, condition: str
) -> None:
    with TestClient(create_app(database_url)) as client:
        result = post(client, "/api/prices", price_payload(condition=condition))
        assert result.status_code == 422
        assert client.get("/api/listings").json() == []


def test_concurrent_first_prices_for_one_offer_create_a_single_offer(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:

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
        assert len({result["id"] for result in results}) == 1
        [offer] = with_history(client)
        assert len(offer["observations"]) == 4


def test_migration_normalizes_conditions_and_merges_offers_that_become_duplicates(
    database_url: str,
) -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.attributes["database_url"] = database_url
    command.downgrade(config, "0006")
    engine = create_engine(database_url)
    legacy = [
        ("Shop", "seller_refurbished", 18000, "2026-09-01T12:00:00Z"),
        ("Shop", "refurbished", 17000, "2026-09-02T12:00:00Z"),
        ("Shop", "open_box", 15000, "2026-09-01T12:00:00Z"),
        ("Other shop", "unknown", 16000, "2026-09-01T12:00:00Z"),
    ]
    with engine.begin() as connection:
        for seller, condition, price, observed_at in legacy:
            listing_id = uuid4()
            connection.execute(
                text(
                    "INSERT INTO listings (id, title, mpn, seller, capacity_tb, condition, revision)"
                    " VALUES (:id, 'Exos X18', 'ST18000NM000J', :seller, 18, :condition, 1)"
                ),
                {"id": listing_id, "seller": seller, "condition": condition},
            )
            connection.execute(
                text(
                    "INSERT INTO observations (id, listing_id, item_price_cents, shipping_cents,"
                    " fee_cents, availability, observed_at, entered_at, notes)"
                    " VALUES (:id, :listing_id, :price, 0, 0, 'in_stock', :at, :at, '')"
                ),
                {"id": uuid4(), "listing_id": listing_id, "price": price, "at": observed_at},
            )
    engine.dispose()
    command.upgrade(config, "head")
    with TestClient(create_app(database_url)) as client:
        offers = {(o["seller"], o["condition"]): o for o in with_history(client)}
    assert set(offers) == {("Shop", "refurbished"), ("Shop", "used"), ("Other shop", "refurbished")}
    merged = offers[("Shop", "refurbished")]["observations"]
    assert [o["item_price_cents"] for o in merged] == [18000, 17000]


def test_deleting_a_wrong_price_removes_it_and_deleting_the_last_price_removes_the_offer(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        post(client, "/api/prices", price_payload())
        typo = post(
            client,
            "/api/prices",
            price_payload(item_price_cents=1890, observed_at="2026-09-22T12:00:00Z"),
        ).json()
        path = f"/api/listings/{typo['id']}/observations"
        kept = client.delete(f"{path}/{typo['observations'][1]['id']}")
        assert kept.status_code == 200, kept.text
        assert [o["item_price_cents"] for o in kept.json()["observations"]] == [18900]
        assert kept.json()["latest"]["item_price_cents"] == 18900
        assert client.delete(f"{path}/{uuid4()}").status_code == 404
        gone = client.delete(f"{path}/{typo['observations'][0]['id']}")
        assert gone.status_code == 204
        assert client.get("/api/listings").json() == []


def test_deleting_an_offer_removes_it_and_its_prices(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        offer = post(client, "/api/prices", price_payload()).json()
        kept = post(client, "/api/prices", price_payload(seller="Other seller")).json()
        assert client.delete(f"/api/listings/{offer['id']}").status_code == 204
        assert [o["id"] for o in client.get("/api/listings").json()] == [kept["id"]]
        assert client.delete(f"/api/listings/{offer['id']}").status_code == 404


def test_editing_an_offer_updates_its_details_in_place(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        offer = post(client, "/api/prices", price_payload()).json()
        path = f"/api/listings/{offer['id']}"
        edited = client.patch(path, json={"title": "Exos X18 18TB", "url": None})
        assert edited.status_code == 200, edited.text
        assert edited.json()["title"] == "Exos X18 18TB"
        assert edited.json()["url"] is None
        assert client.get(path).json() == edited.json()
        assert client.patch(path, json={"seller": "Someone else"}).status_code == 422
        assert client.patch(path, json={"capacity_gb": 20000}).status_code == 422
        assert client.patch(f"/api/listings/{uuid4()}", json={"title": "x"}).status_code == 404


def test_replacing_a_drives_plain_specifications_updates_every_offer_for_that_mpn(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        offer = post(client, "/api/prices", price_payload()).json()
        assert offer["drive"]["specifications"] == {
            "media_type": "unknown",
            "form_factor": "unknown",
            "interface": "unknown",
            "recording_type": "unknown",
            "intended_use": [],
        }
        post(client, "/api/prices", price_payload(seller="Other seller"))
        path = f"/api/drives/{offer['drive']['id']}/specifications"
        specifications = {
            "media_type": "hdd",
            "form_factor": "3_5",
            "interface": "sata",
            "recording_type": "cmr",
            "intended_use": ["nas"],
        }
        saved = client.put(path, json={"capacity_gb": 20000, "specifications": specifications})
        assert saved.status_code == 200, saved.text
        assert saved.json()["specifications"] == specifications
        assert saved.json()["capacity_gb"] == 20000
        offers = client.get("/api/listings").json()
        assert [o["drive"]["specifications"] for o in offers] == [specifications, specifications]
        assert {o["latest"]["price_per_tb"] for o in offers} == {"9.95"}
        for rejected in (
            {**specifications, "interface": "sata-express"},
            {**specifications, "recording_type": {"value": "cmr", "verification": "verified"}},
            {**specifications, "intended_use": ["nas", "toaster"]},
            {**specifications, "media_type": "floppy"},
            {**specifications, "form_factor": "5_25"},
        ):
            response = client.put(path, json={"capacity_gb": 20000, "specifications": rejected})
            assert response.status_code == 422, rejected
        missing = client.put(
            f"/api/drives/{uuid4()}/specifications",
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
    with TestClient(create_app(database_url)) as client:
        drive = post(client, "/api/scraped", scraped_payload(brand="Dell")).json()
        offer = client.get("/api/listings").json()[0]
        path = f"/api/drives/{offer['drive']['id']}/specifications"
        body = {"capacity_gb": 18000, "specifications": specifications}
        named = client.put(path, json={**body, "brand": "  Seagate "})
        post(
            client,
            "/api/scraped",
            scraped_payload(brand="Dell", observed_at="2026-09-23T12:00:00Z"),
        )
        after_a_run = client.get("/api/listings").json()[0]["drive"]["brand"]
        # Left out, the brand stays; blank clears it, for a source to name it again.
        untouched = client.put(path, json=body)
        cleared = client.put(path, json={**body, "brand": "  "})
        too_long = client.put(path, json={**body, "brand": "x" * 61})

    assert drive["status"] == "recorded"
    assert (named.status_code, named.json()["brand"]) == (200, "Seagate")
    assert (after_a_run, untouched.json()["brand"]) == ("Seagate", "Seagate")
    assert (cleared.json()["brand"], too_long.status_code) == (None, 422)


def test_migration_keeps_only_the_plain_value_of_each_specification(database_url: str) -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.attributes["database_url"] = database_url
    command.downgrade(config, "0011")
    engine = create_engine(database_url)
    evidence = {
        "interface": {"value": "sata", "verification": "verified", "source_url": "https://x.io"},
        "recording_type": {"value": "other", "other": "HAMR"},
        "intended_use": {"value": ["nas", "other"], "other": "Cold storage"},
        "smr_management": {"value": "unknown"},
    }
    with engine.begin() as connection:
        drive_id, listing_id = uuid4(), uuid4()
        connection.execute(
            text(
                "INSERT INTO drives (id, mpn, capacity_tb, specifications)"
                " VALUES (:id, 'ST18000NM000J', 18, CAST(:specs AS jsonb))"
            ),
            {"id": drive_id, "specs": json.dumps(evidence)},
        )
        connection.execute(
            text(
                "INSERT INTO listings (id, title, mpn, retailer, seller, condition, drive_id)"
                " VALUES (:id, 'Exos X18', 'ST18000NM000J', 'other', 'shop', 'new', :drive)"
            ),
            {"id": listing_id, "drive": drive_id},
        )
        connection.execute(
            text(
                "INSERT INTO observations (id, listing_id, item_price_cents, shipping_cents,"
                " observed_at, entered_at, notes) VALUES (:id, :listing, 18000, 0, now(), now(), '')"
            ),
            {"id": uuid4(), "listing": listing_id},
        )
    engine.dispose()
    command.upgrade(config, "head")
    with TestClient(create_app(database_url)) as client:
        [offer] = client.get("/api/listings").json()
    assert offer["drive"]["specifications"] == {
        "media_type": "unknown",
        "form_factor": "unknown",
        "interface": "sata",
        "recording_type": "unknown",
        "intended_use": ["nas"],
    }


def test_capacity_belongs_to_the_drive_so_every_offer_for_an_mpn_shares_it(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        first = post(client, "/api/prices", price_payload()).json()
        assert first["capacity_gb"] == 18000
        assert first["drive"]["capacity_gb"] == 18000
        reused = post(client, "/api/prices", price_payload(seller="Other seller", capacity_gb=None))
        assert reused.status_code == 201, reused.text
        assert reused.json()["capacity_gb"] == 18000
        assert reused.json()["latest"]["price_per_tb"] == "11.06"
        mismatch = post(client, "/api/prices", price_payload(seller="Third", capacity_gb=20000))
        assert mismatch.status_code == 409
        assert mismatch.json()["detail"] == (
            "MPN ST18000NM000J is recorded as 18 TB."
            " Edit the drive's specifications to change its capacity."
        )
        unknown = post(client, "/api/prices", price_payload(mpn="ST20000NM007D", capacity_gb=None))
        assert unknown.status_code == 422
        assert unknown.json()["detail"][0]["loc"] == ["body", "capacity_gb"]
        assert len(client.get("/api/listings").json()) == 2


def test_migration_gives_each_drive_the_capacity_most_of_its_offers_recorded(
    database_url: str,
) -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.attributes["database_url"] = database_url
    command.downgrade(config, "0009")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        drive_id = uuid4()
        connection.execute(
            text("INSERT INTO drives (id, mpn) VALUES (:id, 'ST18000NM000J')"), {"id": drive_id}
        )
        for seller, capacity in [("a", 18), ("b", 18), ("c", 20)]:
            listing_id = uuid4()
            connection.execute(
                text(
                    "INSERT INTO listings (id, title, mpn, retailer, seller, capacity_tb,"
                    " condition, drive_id) VALUES (:id, 'Exos X18', 'ST18000NM000J', 'ebay',"
                    " :seller, :capacity, 'new', :drive)"
                ),
                {"id": listing_id, "seller": seller, "capacity": capacity, "drive": drive_id},
            )
            connection.execute(
                text(
                    "INSERT INTO observations (id, listing_id, item_price_cents, shipping_cents,"
                    " fee_cents, availability, observed_at, entered_at, notes) VALUES (:id,"
                    " :listing, 18000, 0, 0, 'in_stock', now(), now(), '')"
                ),
                {"id": uuid4(), "listing": listing_id},
            )
    engine.dispose()
    command.upgrade(config, "head")
    with TestClient(create_app(database_url)) as client:
        offers = client.get("/api/listings").json()
    assert {o["capacity_gb"] for o in offers} == {18000}
    assert {o["latest"]["price_per_tb"] for o in offers} == {"10.00"}


def test_migration_folds_fees_into_shipping_and_drops_prices_without_an_item_price(
    database_url: str,
) -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.attributes["database_url"] = database_url
    command.downgrade(config, "0010")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        drive_id = uuid4()
        connection.execute(
            text("INSERT INTO drives (id, mpn, capacity_tb) VALUES (:id, 'ST18000NM000J', 18)"),
            {"id": drive_id},
        )
        for seller, prices in [
            ("priced", [(18000, 1000, 250, 1), (17000, None, None, 2), (None, 0, 0, 3)]),
            ("never priced", [(None, None, None, 1)]),
        ]:
            listing_id = uuid4()
            connection.execute(
                text(
                    "INSERT INTO listings (id, title, mpn, retailer, seller, condition, drive_id)"
                    " VALUES (:id, 'Exos X18', 'ST18000NM000J', 'other', :seller, 'new', :drive)"
                ),
                {"id": listing_id, "seller": seller, "drive": drive_id},
            )
            for item, shipping, fee, day in prices:
                connection.execute(
                    text(
                        "INSERT INTO observations (id, listing_id, item_price_cents,"
                        " shipping_cents, fee_cents, availability, observed_at, entered_at,"
                        " notes) VALUES (:id, :listing, :item, :shipping, :fee, 'in_stock',"
                        " :at, :at, '')"
                    ),
                    {
                        "id": uuid4(),
                        "listing": listing_id,
                        "item": item,
                        "shipping": shipping,
                        "fee": fee,
                        "at": f"2026-09-0{day}T12:00:00Z",
                    },
                )
    engine.dispose()
    command.upgrade(config, "head")
    with TestClient(create_app(database_url)) as client:
        [offer] = with_history(client)
    assert offer["seller"] == "priced"
    assert [o["shipping_cents"] for o in offer["observations"]] == [1250, 0]
    assert [o["total_cents"] for o in offer["observations"]] == [19250, 17000]


def test_later_prices_never_overwrite_the_title_or_url_an_offer_was_created_with(
    database_url: str,
) -> None:
    untitled = price_payload()
    del untitled["title"]
    with TestClient(create_app(database_url)) as client:
        first = post(client, "/api/prices", untitled)
        assert first.status_code == 201, first.text
        assert first.json()["title"] == "ST18000NM000J"
        client.patch(f"/api/listings/{first.json()['id']}", json={"title": "Exos X18"})
        later = post(client, "/api/prices", {**untitled, "observed_at": "2026-09-22T12:00:00Z"})
        assert later.json()["title"] == "Exos X18"
        retitled = post(
            client,
            "/api/prices",
            price_payload(title="Scraped title", url="https://example.com/?ref=1"),
        )
        assert retitled.json()["title"] == "Exos X18"
        assert retitled.json()["url"] == "https://example.com/disk"


def test_an_unchanged_price_only_updates_when_the_offer_was_last_checked(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        first = post(client, "/api/prices", price_payload()).json()
        assert first["last_checked_at"] == "2026-09-21T12:00:00Z"
        same = post(client, "/api/prices", price_payload(observed_at="2026-09-22T12:00:00Z")).json()
        assert len(same["observations"]) == 1
        assert same["last_checked_at"] == "2026-09-22T12:00:00Z"
        changed = post(
            client,
            "/api/prices",
            price_payload(item_price_cents=17900, observed_at="2026-09-23T12:00:00Z"),
        ).json()
        assert [o["item_price_cents"] for o in changed["observations"]] == [18900, 17900]
        assert changed["last_checked_at"] == "2026-09-23T12:00:00Z"
        assert client.get(f"/api/listings/{first['id']}").json() == changed


def test_unknown_shipping_stays_distinct_from_free_while_totals_stay_known(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        unknown = post(client, "/api/prices", price_payload(shipping_cents=None)).json()["latest"]
        assert unknown["shipping_cents"] is None
        assert unknown["shipping_known"] is False
        assert unknown["total_cents"] == 18900
        assert unknown["price_per_tb"] == "10.50"
        free_payload = price_payload(seller="Free shipper")
        del free_payload["shipping_cents"]
        free = post(client, "/api/prices", free_payload).json()["latest"]
        assert (free["shipping_cents"], free["shipping_known"]) == (0, True)


def test_a_sold_out_offer_keeps_its_last_price_and_is_marked_out_of_stock(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        post(client, "/api/prices", price_payload())
        sold_out = price_payload(in_stock=False, observed_at="2026-09-22T12:00:00Z")
        del sold_out["item_price_cents"], sold_out["shipping_cents"]
        offer = post(client, "/api/prices", sold_out).json()
        assert len(offer["observations"]) == 2
        latest = offer["latest"]
        assert latest["in_stock"] is False
        assert (latest["item_price_cents"], latest["shipping_cents"], latest["total_cents"]) == (
            18900,
            1000,
            19900,
        )
        still_sold_out = {**sold_out, "observed_at": "2026-09-23T12:00:00Z"}
        again = post(client, "/api/prices", still_sold_out).json()
        assert len(again["observations"]) == 2
        assert again["last_checked_at"] == "2026-09-23T12:00:00Z"
        back = post(
            client,
            "/api/prices",
            price_payload(item_price_cents=18500, observed_at="2026-09-24T12:00:00Z"),
        ).json()
        assert [o["in_stock"] for o in back["observations"]] == [True, False, True]
        never_priced = post(client, "/api/prices", {**sold_out, "seller": "New seller"})
        assert never_priced.status_code == 422
        assert never_priced.json()["detail"][0]["loc"] == ["body", "item_price_cents"]


def test_mpns_are_normalized_so_spacing_and_case_do_not_split_a_drive(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        first = post(client, "/api/prices", price_payload(mpn=" st18000 nm000j ")).json()
        assert first["mpn"] == "ST18000NM000J"
        second = post(client, "/api/prices", price_payload(seller="Other seller")).json()
        assert second["drive"]["id"] == first["drive"]["id"]
        assert first["drive"]["aliases"] == []


def test_an_alias_merges_a_variant_mpn_into_its_drive_and_routes_later_prices(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        variant = post(
            client, "/api/prices", price_payload(mpn="ST18000NM000J-2E3101", seller="Shop A")
        ).json()
        post(
            client,
            "/api/prices",
            price_payload(mpn="ST18000NM000J-2E3101", item_price_cents=17000, seller="Shop B"),
        )
        canonical = post(
            client,
            "/api/prices",
            price_payload(seller="Shop B", observed_at="2026-09-20T12:00:00Z"),
        ).json()
        path = f"/api/drives/{canonical['drive']['id']}/aliases"
        added = client.post(path, json={"mpn": "st18000nm000j-2e3101"})
        assert added.status_code == 201, added.text
        assert added.json()["aliases"] == ["ST18000NM000J-2E3101"]
        offers = {o["seller"]: o for o in with_history(client)}
        assert set(offers) == {"Shop A", "Shop B"}
        assert {o["mpn"] for o in offers.values()} == {"ST18000NM000J"}
        assert {o["drive"]["id"] for o in offers.values()} == {canonical["drive"]["id"]}
        assert [o["item_price_cents"] for o in offers["Shop B"]["observations"]] == [18900, 17000]
        later = post(
            client,
            "/api/prices",
            price_payload(
                mpn="ST18000NM000J-2E3101",
                item_price_cents=16000,
                seller="Shop A",
                observed_at="2026-09-25T12:00:00Z",
            ),
        ).json()
        assert later["id"] == variant["id"]
        assert later["mpn"] == "ST18000NM000J"
        assert client.post(path, json={"mpn": "ST18000NM000J"}).status_code == 409
        missing = client.post(f"/api/drives/{uuid4()}/aliases", json={"mpn": "X"})
        assert missing.status_code == 404


def test_migration_normalizes_existing_mpns(database_url: str) -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.attributes["database_url"] = database_url
    command.downgrade(config, "0015")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        drive_id, listing_id = uuid4(), uuid4()
        connection.execute(
            text("INSERT INTO drives (id, mpn, capacity_tb) VALUES (:id, ' st18000nm000j', 18)"),
            {"id": drive_id},
        )
        connection.execute(
            text(
                "INSERT INTO listings (id, title, mpn, retailer, seller, condition, drive_id)"
                " VALUES (:id, 'Exos', ' st18000nm000j', 'other', 'shop', 'new', :drive)"
            ),
            {"id": listing_id, "drive": drive_id},
        )
        connection.execute(
            text(
                "INSERT INTO observations (id, listing_id, item_price_cents, shipping_cents,"
                " observed_at, entered_at, notes) VALUES (:id, :listing, 18000, 0, now(), now(), '')"
            ),
            {"id": uuid4(), "listing": listing_id},
        )
    engine.dispose()
    command.upgrade(config, "head")
    with TestClient(create_app(database_url)) as client:
        [offer] = client.get("/api/listings").json()
    assert (offer["mpn"], offer["drive"]["mpn"]) == ("ST18000NM000J", "ST18000NM000J")


def scraped_payload(**fields: Any) -> dict[str, Any]:
    return {
        "source": "serverpartdeals",
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


def test_the_review_queue_can_be_read_a_part_at_a_time_by_source_and_reason(
    database_url: str,
) -> None:
    """So whatever works through a long queue, a person or a program, can take it in batches."""
    with TestClient(create_app(database_url)) as client:
        for number, (source, mpn, condition) in enumerate(
            [
                ("serverpartdeals", None, "new"),
                ("goharddrive", None, "new"),
                ("goharddrive", "ST18000NM000J", None),
                ("goharddrive", None, "new"),
            ]
        ):
            queued = client.post(
                "/api/scraped",
                json=scraped_payload(
                    source=source,
                    mpn=mpn,
                    condition=condition,
                    url=f"https://store.test/drive-{number}",
                    observed_at=f"2026-09-21T12:0{number}:00Z",
                ),
                headers={"Idempotency-Key": str(uuid4())},
            )
            assert queued.status_code == 202, queued.text

        def queue(**query: Any) -> tuple[list[str], str]:
            answer = client.get("/api/unmatched", params=query)
            assert answer.status_code == 200, answer.text
            return [item["url"][-1] for item in answer.json()], answer.headers["X-Total-Count"]

        # Newest first, as before; the header counts what the filters match, not the page.
        assert queue() == (["3", "2", "1", "0"], "4")
        assert queue(source="goharddrive") == (["3", "2", "1"], "3")
        assert queue(source="goharddrive", reason="missing_mpn") == (["3", "1"], "2")
        assert queue(reason="missing_condition") == (["2"], "1")
        assert queue(limit=2) == (["3", "2"], "4")
        assert queue(limit=2, offset=2) == (["1", "0"], "4")
        assert queue(source="goharddrive", limit=1, offset=2) == (["1"], "3")
        refused = [
            client.get("/api/unmatched", params=query).status_code
            for query in ({"limit": 0}, {"limit": 501}, {"offset": -1}, {"reason": "bored"})
        ]
        assert refused == [422, 422, 422, 422]


def test_a_sold_out_scraped_offer_records_only_that_it_is_out_of_stock(
    database_url: str,
) -> None:
    placeholder = {"in_stock": False, "item_price_cents": 1_000_000}
    with TestClient(create_app(database_url)) as client:
        unseen = post(client, "/api/scraped", scraped_payload(**placeholder))
        nothing = client.get("/api/listings").json()
        post(client, "/api/scraped", scraped_payload())
        sold_out = post(
            client,
            "/api/scraped",
            scraped_payload(**placeholder, observed_at="2026-09-22T12:00:00Z"),
        )
        [offer] = client.get("/api/listings").json()

    # Never seen in stock, it has no real price to track yet.
    assert (unseen.status_code, unseen.json()["status"], nothing) == (200, "ignored", [])
    assert sold_out.json()["status"] == "recorded"
    # Sold out, it keeps the price it last had in stock: the store's sold-out price is ignored.
    assert (offer["latest"]["in_stock"], offer["latest"]["item_price_cents"]) == (False, 36999)
    assert offer["last_checked_at"] == "2026-09-22T12:00:00Z"


def test_a_scraped_offer_with_an_mpn_and_condition_is_recorded_as_a_sourced_price(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        result = post(client, "/api/scraped", scraped_payload())
        assert result.status_code == 201, result.text
        assert result.json()["status"] == "recorded"
        [offer] = client.get("/api/listings").json()
        assert result.json()["listing_id"] == offer["id"]
        assert (offer["mpn"], offer["store"], offer["condition"]) == (
            "ST18000NM000J",
            "serverpartdeals",
            "manufacturer_recertified",
        )
        assert offer["latest"]["item_price_cents"] == 36999
        assert offer["latest"]["acquisition_method"] == "serverpartdeals"
        manual = post(client, "/api/prices", price_payload(seller="Manual shop")).json()
        assert manual["latest"]["acquisition_method"] == "manual"


def test_scraped_offers_that_cannot_be_matched_wait_in_the_review_queue(database_url: str) -> None:
    base = "https://www.serverpartdeals.com/products/"
    with TestClient(create_app(database_url)) as client:
        first = post(client, "/api/scraped", scraped_payload(mpn=None, url=base + "mystery"))
        assert first.status_code == 202, first.text
        assert first.json()["status"] == "queued"
        again = post(
            client,
            "/api/scraped",
            scraped_payload(
                mpn=None,
                url=base + "mystery",
                item_price_cents=35999,
                observed_at="2026-09-22T12:00:00Z",
            ),
        )
        assert again.json()["unmatched_id"] == first.json()["unmatched_id"]
        post(client, "/api/scraped", scraped_payload(url=base + "odd-condition", condition=None))
        post(client, "/api/scraped", scraped_payload())
        post(
            client,
            "/api/scraped",
            scraped_payload(url=base + "wrong-capacity", seller="x", capacity_gb=20000),
        )
        post(
            client,
            "/api/scraped",
            scraped_payload(url=base + "new-drive", mpn="ST20000NM007D", capacity_gb=None),
        )
        queue = {item["url"]: item for item in client.get("/api/unmatched").json()}
        assert {url.removeprefix(base): item["reason"] for url, item in queue.items()} == {
            "mystery": "missing_mpn",
            "odd-condition": "missing_condition",
            "wrong-capacity": "capacity_conflict",
            "new-drive": "missing_capacity",
        }
        mystery = queue[base + "mystery"]
        assert (mystery["source"], mystery["title"]) == (
            "serverpartdeals",
            scraped_payload()["title"],
        )
        assert (mystery["item_price_cents"], mystery["last_seen_at"]) == (
            35999,
            "2026-09-22T12:00:00Z",
        )
        assert len(client.get("/api/listings").json()) == 1


def test_a_queued_offer_leaves_the_review_queue_once_a_later_scrape_of_it_is_recorded(
    database_url: str,
) -> None:
    base = "https://www.serverpartdeals.com/products/"
    with TestClient(create_app(database_url)) as client:
        post(client, "/api/scraped", scraped_payload(mpn=None, url=base + "mystery"))
        post(client, "/api/scraped", scraped_payload(mpn=None, url=base + "another"))
        later = post(client, "/api/scraped", scraped_payload(url=base + "mystery"))
        assert later.status_code == 201, later.text
        assert [item["url"] for item in client.get("/api/unmatched").json()] == [base + "another"]


def test_resolving_a_queued_offer_records_it_and_later_scrapes_match_directly(
    database_url: str,
) -> None:
    url = "https://www.serverpartdeals.com/products/mystery"
    with TestClient(create_app(database_url)) as client:
        queued = post(client, "/api/scraped", scraped_payload(mpn=None, condition=None, url=url))
        item_id = queued.json()["unmatched_id"]
        resolved = client.post(
            f"/api/unmatched/{item_id}/resolve",
            json={
                "mpn": "st18000nm000j",
                "condition": "manufacturer_recertified",
                "capacity_gb": 18000,
            },
        )
        assert resolved.status_code == 200, resolved.text
        offer = resolved.json()
        assert (offer["mpn"], offer["latest"]["item_price_cents"]) == ("ST18000NM000J", 36999)
        assert offer["latest"]["acquisition_method"] == "serverpartdeals"
        assert client.get("/api/unmatched").json() == []
        later = post(
            client,
            "/api/scraped",
            scraped_payload(
                mpn=None,
                condition=None,
                url=url,
                item_price_cents=34999,
                observed_at="2026-09-22T12:00:00Z",
            ),
        )
        assert later.status_code == 201, later.text
        assert later.json()["listing_id"] == offer["id"]
        saved = client.get(f"/api/listings/{offer['id']}").json()
        assert [o["item_price_cents"] for o in saved["observations"]] == [36999, 34999]
        missing = client.post(
            f"/api/unmatched/{uuid4()}/resolve",
            json={"mpn": "X", "condition": "new", "capacity_gb": 1000},
        )
        assert missing.status_code == 404


def test_ignoring_a_queued_offer_keeps_later_scrapes_of_it_out_of_the_queue(
    database_url: str,
) -> None:
    url = "https://www.serverpartdeals.com/products/not-a-drive"
    with TestClient(create_app(database_url)) as client:
        queued = post(client, "/api/scraped", scraped_payload(mpn=None, url=url)).json()
        assert client.post(f"/api/unmatched/{queued['unmatched_id']}/ignore").status_code == 204
        assert client.get("/api/unmatched").json() == []
        later = post(client, "/api/scraped", scraped_payload(mpn=None, url=url))
        assert later.status_code == 200
        assert later.json() == {"status": "ignored", "listing_id": None, "unmatched_id": None}
        assert client.get("/api/unmatched").json() == []
        assert client.get("/api/listings").json() == []


def test_a_scraped_offer_can_declare_other_mpns_for_its_drive(database_url: str) -> None:
    base = "https://www.serverpartdeals.com/products/"
    with TestClient(create_app(database_url)) as client:
        oem = post(
            client,
            "/api/scraped",
            scraped_payload(
                url=base + "dell-g14", mpn="0HNHWC", capacity_gb=16000, condition="new"
            ),
        ).json()
        maker = post(
            client,
            "/api/scraped",
            scraped_payload(
                url=base + "bare",
                mpn="WUH721816AL5205",
                aliases=["0hnhwc"],
                capacity_gb=16000,
                condition="refurbished",
            ),
        )
        assert maker.status_code == 201, maker.text
        offers = {o["id"]: o for o in client.get("/api/listings").json()}
        assert {o["mpn"] for o in offers.values()} == {"WUH721816AL5205"}
        assert offers[oem["listing_id"]]["drive"]["aliases"] == ["0HNHWC"]
        again = post(
            client,
            "/api/scraped",
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
        later_oem = post(
            client,
            "/api/scraped",
            scraped_payload(
                url=base + "dell-g13", mpn="0HNHWC", capacity_gb=16000, condition="used"
            ),
        ).json()
        assert client.get(f"/api/listings/{later_oem['listing_id']}").json()["mpn"] == (
            "WUH721816AL5205"
        )


def test_a_scraped_alias_already_claimed_by_another_drive_is_left_for_a_person(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        claimed = post(client, "/api/prices", price_payload(mpn="ST18000NM000J")).json()
        drive_id = claimed["drive"]["id"]
        assert (
            client.post(f"/api/drives/{drive_id}/aliases", json={"mpn": "0XYZ"}).status_code == 201
        )

        scraped = post(
            client,
            "/api/scraped",
            scraped_payload(
                url="https://www.serverpartdeals.com/products/other",
                mpn="ST16000NM000J",
                aliases=["0XYZ"],
                capacity_gb=16000,
            ),
        )

        assert scraped.status_code == 201, scraped.text
        drives = {o["mpn"]: o["drive"]["aliases"] for o in client.get("/api/listings").json()}
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


def test_the_published_contract_describes_every_listing_and_scrape_result(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        spec = client.get("/openapi.json").json()

    operations = {
        (path, method): operation["operationId"]
        for path, methods in spec["paths"].items()
        for method, operation in methods.items()
    }
    assert operations[("/api/listings", "get")] == "list_listings"
    assert operations[("/api/scraped", "post")] == "record_scraped"
    summary = response_schema(spec, "/api/listings", "get", "200")
    assert set(summary["required"]) == {
        "id", "title", "mpn", "store", "store_name", "seller", "url", "condition",
        "last_checked_at", "capacity_gb", "drive", "latest",
    }  # fmt: skip
    listing = response_schema(spec, "/api/listings/{listing_id}", "get", "200")
    assert set(listing["required"]) == set(summary["required"]) | {"observations"}
    assert response_schema(spec, "/api/price-history", "get", "200") == listing
    drive = schema_of(spec, listing["properties"]["drive"])
    assert set(drive["required"]) == {
        "id", "mpn", "aliases", "brand", "capacity_gb", "specifications",
    }  # fmt: skip
    latest = schema_of(spec, listing["properties"]["latest"])
    assert set(latest["required"]) == {
        "id", "item_price_cents", "shipping_cents", "shipping_known", "in_stock", "observed_at",
        "entered_at", "notes", "acquisition_method", "total_cents", "price_per_tb",
    }  # fmt: skip
    for status in ("201", "202", "200"):
        result = response_schema(spec, "/api/scraped", "post", status)
        assert set(result["properties"]) == {"status", "listing_id", "unmatched_id"}
        assert result["properties"]["status"]["enum"] == ["recorded", "queued", "ignored"]
    queued = response_schema(spec, "/api/unmatched", "get", "200")
    assert {"id", "source", "url", "reason", "first_seen_at", "last_seen_at"} <= set(
        queued["required"]
    )


def test_listings_carry_each_offers_latest_price_and_history_is_fetched_per_offer(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        first = post(client, "/api/prices", price_payload(seller="Shop A")).json()
        post(
            client,
            "/api/prices",
            price_payload(
                seller="Shop A", item_price_cents=17900, observed_at="2026-09-22T12:00:00Z"
            ),
        )
        other = post(client, "/api/prices", price_payload(seller="Shop B")).json()
        post(client, "/api/prices", price_payload(seller="Shop C"))

        summaries = client.get("/api/listings").json()
        histories = client.get(
            "/api/price-history", params={"listing": [first["id"], other["id"], str(uuid4())]}
        ).json()
        none_asked = client.get("/api/price-history").json()

    assert all("observations" not in summary for summary in summaries)
    latest = {summary["seller"]: summary["latest"]["item_price_cents"] for summary in summaries}
    assert latest == {"Shop A": 17900, "Shop B": 18900, "Shop C": 18900}
    assert {
        history["seller"]: [o["item_price_cents"] for o in history["observations"]]
        for history in histories
    } == {"Shop A": [18900, 17900], "Shop B": [18900]}
    assert none_asked == []


def test_the_western_digital_store_is_a_store(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        saved = post(client, "/api/prices", price_payload(store="westerndigital", seller=""))

    assert saved.status_code == 201, saved.text
    assert saved.json()["store"] == "westerndigital"


def test_listings_can_be_narrowed_to_one_store(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        post(client, "/api/prices", price_payload(store="serverpartdeals", seller=""))
        post(client, "/api/prices", price_payload(store="other", seller="Shop"))

        narrowed = client.get("/api/listings", params={"store": "serverpartdeals"}).json()
        everything = client.get("/api/listings").json()
        unknown = client.get("/api/listings", params={"store": "frys"})

    assert [listing["store"] for listing in narrowed] == ["serverpartdeals"]
    assert sorted(listing["store"] for listing in everything) == ["other", "serverpartdeals"]
    # Stores are data now: a store nothing is recorded under simply lists nothing.
    assert (unknown.status_code, unknown.json()) == (200, [])


def test_small_drives_and_cards_are_tracked_in_whole_gigabytes(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        card = post(
            client,
            "/api/prices",
            price_payload(
                mpn="SDSQXAA-128G", capacity_gb=128, item_price_cents=1999, shipping_cents=0
            ),
        )
        tiny = post(
            client,
            "/api/prices",
            price_payload(
                mpn="SDSQUA4-032G", capacity_gb=32, item_price_cents=599, shipping_cents=0
            ),
        )

    assert card.status_code == 201, card.text
    assert (card.json()["capacity_gb"], card.json()["latest"]["price_per_tb"]) == (128, "156.17")
    assert (tiny.json()["capacity_gb"], tiny.json()["latest"]["price_per_tb"]) == (32, "187.19")


def test_a_scraped_offer_names_its_drive_s_brand_until_one_is_known(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        manual = post(client, "/api/prices", price_payload(mpn="WD120EFBX", capacity_gb=12000))
        assert manual.json()["drive"]["brand"] is None
        first = post(client, "/api/scraped", scraped_payload(brand="Seagate"))
        later = post(
            client,
            "/api/scraped",
            scraped_payload(
                brand="Dell", item_price_cents=35999, observed_at="2026-09-23T12:00:00Z"
            ),
        )
        unnamed = post(
            client,
            "/api/scraped",
            scraped_payload(mpn="WD120EFBX", capacity_gb=12000, url="https://spd.test/wd"),
        )
        brands = {o["mpn"]: o["drive"]["brand"] for o in client.get("/api/listings").json()}
        too_long = post(client, "/api/scraped", scraped_payload(brand="x" * 61))

    assert (first.status_code, later.status_code, unnamed.status_code) == (201, 201, 201)
    assert brands == {"ST18000NM000J": "Seagate", "WD120EFBX": None}
    assert too_long.status_code == 422


def test_a_scraped_offer_fills_in_specifications_nobody_has_entered(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        first = post(
            client,
            "/api/scraped",
            scraped_payload(
                specifications={"media_type": "hdd", "form_factor": "3_5", "interface": "sas"}
            ),
        )
        assert first.status_code == 201, first.text
        drive = client.get(f"/api/listings/{first.json()['listing_id']}").json()["drive"]
        assert drive["specifications"] == {
            "media_type": "hdd",
            "form_factor": "3_5",
            "interface": "sas",
            "recording_type": "unknown",
            "intended_use": [],
        }
        entered = {**drive["specifications"], "interface": "sata", "intended_use": ["nas"]}
        client.put(
            f"/api/drives/{drive['id']}/specifications",
            json={"capacity_gb": 18000, "specifications": entered},
        )

        later = post(
            client,
            "/api/scraped",
            scraped_payload(
                item_price_cents=35999,
                observed_at="2026-09-23T12:00:00Z",
                specifications={"interface": "sas", "recording_type": "cmr"},
            ),
        )

        assert later.status_code == 201, later.text
        after = client.get(f"/api/listings/{later.json()['listing_id']}").json()["drive"]
        assert after["specifications"] == {**entered, "recording_type": "cmr"}


def run_report(source: str, finished_at: str, **fields: Any) -> dict[str, Any]:
    return {
        "source": source,
        "started_at": "2026-09-27T08:00:00Z",
        "finished_at": finished_at,
        "completed": True,
        "seen": 3,
        "recorded": 2,
        "queued": 1,
        "ignored": 0,
        "failed": 0,
        "rechecked": 1,
        "recheck_failed": 0,
        "stopped": False,
        **fields,
    }


def test_the_latest_run_of_each_collector_source_is_kept(database_url: str) -> None:
    earlier = run_report("serverpartdeals", "2026-09-27T08:10:00Z")
    later = run_report("serverpartdeals", "2026-09-27T16:10:00Z", completed=False, seen=1)
    other = run_report("goharddrive", "2026-09-27T08:40:00Z")
    with TestClient(create_app(database_url)) as client:
        assert client.get("/api/collector-runs/latest").json() == []
        for report in (later, earlier, other):
            saved = client.post("/api/collector-runs", json=report)
            assert saved.status_code == 201, saved.text
            assert saved.json() == report
        latest = client.get("/api/collector-runs/latest").json()

    assert latest == [other, later]


@pytest.mark.parametrize(
    "report",
    [
        run_report("serverpartdeals", "2026-09-27T16:10:00Z", seen=-1),
        run_report("serverpartdeals", "2026-09-27T16:10:00"),
        run_report("", "2026-09-27T16:10:00Z"),
    ],
    ids=["negative count", "time without a timezone", "no source"],
)
def test_a_run_report_that_is_not_a_run_is_rejected(
    database_url: str, report: dict[str, Any]
) -> None:
    with TestClient(create_app(database_url)) as client:
        rejected = client.post("/api/collector-runs", json=report)
        stored = client.get("/api/collector-runs/latest").json()

    assert (rejected.status_code, stored) == (422, [])


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
    with TestClient(create_app(database_url)) as client:
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


@pytest.mark.parametrize(
    ("rule", "field"),
    [
        ({"pattern": "(unclosed", "condition": "used"}, "pattern"),
        ({"pattern": "", "condition": "used"}, "pattern"),
        ({"pattern": r"\bmint\b", "condition": "mint"}, "condition"),
    ],
)
def test_a_condition_rule_that_cannot_work_is_refused_on_its_field(
    database_url: str, rule: dict[str, str], field: str
) -> None:
    with TestClient(create_app(database_url)) as client:
        refused = client.put("/api/condition-rules", json=[SEEDED_CONDITION_RULES[0], rule])
        kept = client.get("/api/condition-rules").json()

    assert refused.status_code == 422
    assert [issue["loc"] for issue in refused.json()["detail"]] == [["body", 1, field]]
    assert kept == SEEDED_CONDITION_RULES


def test_pasted_listing_text_is_read_into_the_fields_of_an_offer(database_url: str) -> None:
    pasted = (
        "\n  Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive  \n"
        "Was $299.99\n$1,219.99\nIn stock\n"
    )
    with TestClient(create_app(database_url)) as client:
        read = client.post("/api/listing-text", json={"text": pasted})
        nothing = client.post("/api/listing-text", json={"text": "hello"})
        empty = client.post("/api/listing-text", json={"text": "  "})

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
    assert empty.status_code == 422


def test_every_store_is_a_source_and_offers_are_recorded_under_and_named_by_one(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        by_hand = client.post("/api/sources", json={"name": "Server Orbit!", "kind": "manual"})
        unknown = post(client, "/api/prices", price_payload(store="nowhere", seller=""))
        offer = post(client, "/api/prices", price_payload(store="serverorbit", seller=""))
        due_now = client.get("/api/sources/due").json()
        no_stores = client.get("/api/stores")

    assert by_hand.status_code == 201, by_hand.text
    assert {name: by_hand.json()[name] for name in ("key", "kind", "base_url", "settings",
                                                    "next_run_at")} == {
        "key": "serverorbit", "kind": "manual", "base_url": "", "settings": {}, "next_run_at": None,
    }  # fmt: skip
    assert unknown.status_code == 422
    assert unknown.json()["detail"][0]["loc"] == ["body", "store"]
    assert offer.status_code == 201, offer.text
    assert (offer.json()["store"], offer.json()["store_name"]) == (
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
        "notes": "",
        **fields,
    }


def names(sources: list[dict[str, Any]]) -> set[str]:
    return {source["name"] for source in sources}


def test_sources_are_added_listed_and_edited_with_their_next_scheduled_run(
    database_url: str,
) -> None:
    before = datetime.now(UTC)
    with TestClient(create_app(database_url)) as client:
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
    return names(client.get("/api/sources/due").json())


def report_run_of(client: TestClient, key: str, started_at: datetime) -> None:
    report = run_report(key, (started_at + timedelta(minutes=5)).isoformat())
    reported = client.post(
        "/api/collector-runs", json={**report, "started_at": started_at.isoformat()}
    )
    assert reported.status_code == 201, reported.text


def test_a_source_is_due_until_it_runs_and_again_once_its_schedule_fires_after_that_run(
    database_url: str,
) -> None:
    now = datetime.now(UTC)
    with TestClient(create_app(database_url)) as client:
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
    with TestClient(create_app(database_url)) as client:
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


def test_a_source_asked_to_run_goes_ahead_of_those_merely_overdue(database_url: str) -> None:
    now = datetime.now(UTC)
    with TestClient(create_app(database_url)) as client:
        asked = client.post("/api/sources", json=source_input()).json()
        client.post("/api/sources", json=source_input(name="Old Run"))
        for key in ("serverpartdeals", "westerndigital", "goharddrive", "serverorbit"):
            report_run_of(client, key, now)
        # Overdue by a day, and so ahead of anything due only now.
        report_run_of(client, "oldrun", now - timedelta(days=2))
        scheduled = [source["name"] for source in client.get("/api/sources/due").json()]
        client.post(f"/api/sources/{asked['id']}/run")
        after_asking = [source["name"] for source in client.get("/api/sources/due").json()]

    assert scheduled == ["Old Run"]
    assert after_asking == ["Server Orbit", "Old Run"]


def activity(source: str, started_at: datetime, **counts: int) -> dict[str, Any]:
    return {
        "source": source,
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "seen": 0,
        "recorded": 0,
        "queued": 0,
        "ignored": 0,
        "failed": 0,
        **counts,
    }


def test_what_the_collector_is_doing_is_known_while_it_does_it(database_url: str) -> None:
    started = datetime.now(UTC).replace(microsecond=0)
    with TestClient(create_app(database_url)) as client:
        unheard = client.get("/api/collector-status").json()
        first = client.put("/api/collector-activity", json=activity("goharddrive", started))
        assert first.status_code == 200, first.text
        client.put(
            "/api/collector-activity",
            json=activity("goharddrive", started, seen=120, recorded=110, queued=6, ignored=4),
        )
        running = client.get("/api/collector-status").json()
        report_run_of(client, "goharddrive", started)
        finished = client.get("/api/collector-status").json()

    # Nothing has been heard from a collector, and every collected store is waiting on one.
    assert unheard["seen_at"] is None
    assert unheard["running"] == []
    assert sorted(unheard["waiting"]) == ["goharddrive", "serverpartdeals", "westerndigital"]
    assert first.json() == {"stop": False}
    [run] = running["running"]
    assert started <= datetime.fromisoformat(run.pop("updated_at")) <= datetime.now(UTC)
    assert run == activity("goharddrive", started, seen=120, recorded=110, queued=6, ignored=4)
    assert sorted(running["waiting"]) == ["serverpartdeals", "westerndigital"]
    assert started <= datetime.fromisoformat(running["seen_at"]) <= datetime.now(UTC)
    # The run's report ends it.
    assert finished["running"] == []
    assert sorted(finished["waiting"]) == ["serverpartdeals", "westerndigital"]


def test_a_collector_asking_what_is_due_is_running_nothing(database_url: str) -> None:
    """A collector restarted partway through a run never reports it: asking what is due is
    what it does between runs, so nothing is left looking as if it were still running."""
    with TestClient(create_app(database_url)) as client:
        client.put("/api/collector-activity", json=activity("goharddrive", datetime.now(UTC)))
        client.get("/api/sources/due")
        status = client.get("/api/collector-status").json()

    assert status["running"] == []
    assert "goharddrive" in status["waiting"]
    assert status["seen_at"] is not None


def test_a_run_in_progress_is_told_to_stop_once_asked_and_recorded_as_stopped(
    database_url: str,
) -> None:
    started = datetime.now(UTC)
    with TestClient(create_app(database_url)) as client:
        source = next(s for s in client.get("/api/sources").json() if s["key"] == "goharddrive")
        progress = activity("goharddrive", started, seen=40, recorded=40)
        before = client.put("/api/collector-activity", json=progress).json()
        asked = client.post(f"/api/sources/{source['id']}/stop")
        after = client.put("/api/collector-activity", json=progress).json()
        report = run_report(
            "goharddrive", (started + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            completed=False, stopped=True, started_at=progress["started_at"],
        )  # fmt: skip
        saved = client.post("/api/collector-runs", json=report)
        # The request was for that run: the next one is not stopped by it.
        later = activity("goharddrive", datetime.now(UTC) + timedelta(hours=8))
        next_run = client.put("/api/collector-activity", json=later).json()
        latest = client.get("/api/collector-runs/latest").json()
        missing = client.post(f"/api/sources/{uuid4()}/stop")

    assert before == {"stop": False}
    assert (asked.status_code, asked.json()["id"]) == (202, source["id"])
    assert after == {"stop": True}
    assert saved.status_code == 201, saved.text
    assert [run["stopped"] for run in latest] == [True]
    assert next_run == {"stop": False}
    assert missing.status_code == 404


def test_progress_that_is_not_progress_is_rejected(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        rejected = client.put(
            "/api/collector-activity", json=activity("goharddrive", datetime.now(UTC), seen=-1)
        )
        status = client.get("/api/collector-status").json()

    assert (rejected.status_code, status["running"]) == (422, [])


@pytest.mark.parametrize(
    ("fields", "field"),
    [
        ({"retailer": "serverpartdeals"}, "retailer"),
        ({"base_url": ""}, "base_url"),
        ({"schedule": "nightly"}, "schedule"),
        ({"transport": "vpn"}, "transport"),
        ({"schedule": "0 3 * *"}, "schedule"),
        ({"kind": "amazon"}, "kind"),
        ({"base_url": "ftp://store.test"}, "base_url"),
    ],
)
def test_a_source_that_cannot_be_collected_is_refused_on_the_field_at_fault(
    database_url: str, fields: dict[str, Any], field: str
) -> None:
    with TestClient(create_app(database_url)) as client:
        refused = client.post("/api/sources", json=source_input(**fields))
        listed = client.get("/api/sources").json()

    assert refused.status_code == 422
    assert [issue["loc"][-1] for issue in refused.json()["detail"]] == [field]
    assert names(listed) == set(SEEDED_SOURCES)


def test_source_names_and_keys_are_unique_and_only_existing_sources_can_be_edited(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        client.post("/api/sources", json=source_input())
        other = client.post("/api/sources", json=source_input(name="Elsewhere")).json()
        duplicate = client.post("/api/sources", json=source_input(schedule="0 4 * * *"))
        same_key = client.post("/api/sources", json=source_input(name="Server-Orbit"))
        renamed_onto = client.put(f"/api/sources/{other['id']}", json=source_input())
        missing = client.put(f"/api/sources/{uuid4()}", json=source_input(name="Nowhere"))

    assert [response.status_code for response in (duplicate, same_key, renamed_onto, missing)] == [
        409, 409, 409, 404,
    ]  # fmt: skip


# A sitemap source whose pages are each one product has nothing to say about embedded data.
NO_EMBEDDED_DATA = dict.fromkeys(
    (
        "data_pattern",
        "data_items",
        "data_model_field",
        "data_name_field",
        "data_price_field",
        "data_brand_field",
        "data_stock_field",
        "data_in_stock_value",
    ),
    "",
)
# Seagate: each page carries a family of models as JSON handed to a script.
EMBEDDED_DATA = {
    "data_pattern": r"product_models = JSON\.parse\('(.*?)'\);",
    "data_items": "*.skus.*",
    "data_model_field": "modelNo",
    "data_name_field": "name",
    "data_price_field": "final_price",
    "data_brand_field": "brand",
}


def test_a_sitemap_source_can_say_where_its_pages_carry_their_products_as_data(
    database_url: str,
) -> None:
    family_pages = source_input(name="Seagate", kind="sitemap", settings=EMBEDDED_DATA)
    with TestClient(create_app(database_url)) as client:
        added = client.post("/api/sources", json=family_pages)

    assert added.status_code == 201, added.text
    # With no stock field, a product is in stock whenever it has a price.
    assert added.json()["settings"] == {
        "sitemap_path": "",
        "product_path_pattern": "",
        "free_shipping_marker": "",
        **EMBEDDED_DATA,
        "data_stock_field": "",
        "data_in_stock_value": "",
    }


def test_each_kind_of_source_keeps_its_own_settings_with_defaults_filled_in(
    database_url: str,
) -> None:
    sitemap = source_input(
        name="Map Two",
        kind="sitemap",
        settings={},
    )
    sap = source_input(
        name="Sap Three",
        kind="sap_commerce",
        settings={"api_url": "https://api.wd.test/wdwebservices/v2", "site": "us"},
    )
    with TestClient(create_app(database_url)) as client:
        shopify = client.post("/api/sources", json=source_input(name="Shop One")).json()
        read = client.post("/api/sources", json=sitemap).json()
        wd = client.post("/api/sources", json=sap).json()

    assert (shopify["key"], read["key"], wd["key"]) == ("shopone", "maptwo", "sapthree")
    assert shopify["settings"] == {
        "collections": ["hard-drives"],
        "free_shipping": False,
    }
    # Blank: the sitemap is found from robots.txt, every page in it is read, and each page is
    # one product read from its own markup.
    assert read["settings"] == {
        "sitemap_path": "",
        "product_path_pattern": "",
        "free_shipping_marker": "",
        **NO_EMBEDDED_DATA,
    }
    assert wd["settings"] == {
        "api_url": "https://api.wd.test/wdwebservices/v2",
        "site": "us",
        "sitemap_path": "",
        "product_path_pattern": "",
        "recertified_sku_prefix": "",
    }


def test_a_source_is_always_given_with_the_settings_its_kind_has_now(database_url: str) -> None:
    """A source saved before a setting existed, or with one since dropped, reads as if saved
    today, so the collector never has to guess a default."""
    saved_long_ago = {"product_path_pattern": "-p/", "title_prefix": "Old Store - "}
    with TestClient(create_app(database_url)) as client:
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
        due_now = client.get("/api/sources/due").json()

    expected = {
        "sitemap_path": "",
        "product_path_pattern": "-p/",
        "free_shipping_marker": "",
        **NO_EMBEDDED_DATA,
    }
    assert [entry["settings"] for entry in listed if entry["id"] == source["id"]] == [expected]
    assert [entry["settings"] for entry in due_now if entry["id"] == source["id"]] == [expected]
    # Settings its kind would refuse are given as saved, for the collector to report.
    assert [entry["settings"] for entry in listed if entry["id"] == broken["id"]] == [{}]


@pytest.mark.parametrize(
    ("kind", "settings", "field"),
    [
        ("shopify", {"collections": []}, "collections"),
        ("sitemap", {"product_path_pattern": "(unclosed"}, "product_path_pattern"),
        ("sitemap", {"sitemap_path": "sitemap.xml"}, "sitemap_path"),
        ("sap_commerce", {"site": "us", "product_path_pattern": "/p/"}, "api_url"),
        # Where a page's data is: a regular expression with a group around the data, and then
        # which fields name, number and price each product.
        ("sitemap", {**EMBEDDED_DATA, "data_pattern": "(unclosed"}, "data_pattern"),
        ("sitemap", {**EMBEDDED_DATA, "data_pattern": "models = "}, "data_pattern"),
        ("sitemap", {**EMBEDDED_DATA, "data_model_field": ""}, "data_model_field"),
        ("sitemap", {**EMBEDDED_DATA, "data_name_field": ""}, "data_name_field"),
        ("sitemap", {**EMBEDDED_DATA, "data_price_field": ""}, "data_price_field"),
        # Worked out by the collector, not set: the title, the store's own brands and codes, which
        # product pages name a capacity, and which pages are recertified.
        ("sitemap", {"title_prefix": "goHardDrive.com - "}, "title_prefix"),
        ("sitemap", {"own_brands": ["Avolusion"]}, "own_brands"),
        ("sitemap", {"product_code_class": "product_code"}, "product_code_class"),
        ("sitemap", {"require_capacity_in_url": True}, "require_capacity_in_url"),
        (
            "sap_commerce",
            {"api_url": "https://api.wd.test", "site": "us", "recertified_path": "/recertified/"},
            "recertified_path",
        ),
        ("shopify", {"collections": ["all"], "site": "us"}, "site"),
        # Worked out by the collector, not set: a SKU in a title is the MPN.
        ("shopify", {"collections": ["all"], "mpn_from_sku": True}, "mpn_from_sku"),
        # Sold-out prices are never recorded, so there is no placeholder to tell apart.
        ("shopify", {"collections": ["all"], "placeholder_price": "10000.00"}, "placeholder_price"),
    ],
)
def test_settings_that_do_not_fit_the_kind_are_refused_on_the_setting(
    database_url: str, kind: str, settings: dict[str, Any], field: str
) -> None:
    with TestClient(create_app(database_url)) as client:
        refused = client.post("/api/sources", json=source_input(kind=kind, settings=settings))

    assert refused.status_code == 422
    assert [issue["loc"][-1] for issue in refused.json()["detail"]] == [field]
    assert refused.json()["detail"][0]["loc"][:2] == ["body", "settings"]


def test_a_collected_source_needs_only_a_name_type_and_url(database_url: str) -> None:
    bare = {"name": "Server Orbit", "kind": "shopify", "base_url": "https://www.serverorbit.com",
            "settings": {"collections": ["hard-drives"]}}  # fmt: skip
    with TestClient(create_app(database_url)) as client:
        added = client.post("/api/sources", json=bare)

    assert added.status_code == 201, added.text
    assert {name: added.json()[name] for name in ("schedule", "enabled", "basis", "transport",
                                                 "notes")} == {
        "schedule": "0 */8 * * *", "enabled": True, "basis": "unconfirmed",
        "transport": "direct", "notes": "",
    }  # fmt: skip


def test_a_source_nothing_is_recorded_under_can_be_deleted_with_its_runs(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        source = client.post("/api/sources", json=source_input()).json()
        report_run_of(client, "serverorbit", datetime.now(UTC))
        deleted = client.delete(f"/api/sources/{source['id']}")
        again = client.delete(f"/api/sources/{source['id']}")
        listed = client.get("/api/sources").json()
        runs = client.get("/api/collector-runs/latest").json()

    assert (deleted.status_code, deleted.content, again.status_code) == (204, b"", 404)
    assert names(listed) == set(SEEDED_SOURCES)
    assert runs == []


def test_a_source_with_offers_or_queued_offers_is_kept_and_so_is_other(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        sources = {source["key"]: source["id"] for source in client.get("/api/sources").json()}
        post(client, "/api/prices", price_payload(store="serverpartdeals", seller=""))
        post(client, "/api/scraped", scraped_payload(source="goharddrive", mpn=None))
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
    with TestClient(create_app(database_url)) as client:
        source = client.post("/api/sources", json=source_input()).json()
        renamed = client.put(
            f"/api/sources/{source['id']}", json=source_input(name="Orbit Refurbished")
        ).json()

    assert (renamed["name"], renamed["key"]) == ("Orbit Refurbished", "serverorbit")


def test_a_price_of_nothing_is_not_a_price_whoever_enters_it(database_url: str) -> None:
    """A store writes 0 for a drive it sells only by quote; recorded, it would be the lowest
    price of everything."""
    with TestClient(create_app(database_url)) as client:
        entered = post(client, "/api/prices", price_payload(item_price_cents=0))
        scraped = post(client, "/api/scraped", scraped_payload(item_price_cents=0))
        # Sold out with a price of nothing is no better: there is no price to carry.
        sold_out = post(client, "/api/scraped", scraped_payload(item_price_cents=0, in_stock=False))
        listings = client.get("/api/listings").json()
        queue = client.get("/api/unmatched").json()

    for refused in (entered, scraped, sold_out):
        assert refused.status_code == 422, refused.text
        [issue] = refused.json()["detail"]
        assert issue["loc"] == ["body", "item_price_cents"]
        assert issue["msg"].endswith("Enter a price above zero.")
    assert (listings, queue) == ([], [])


def test_the_kinds_of_store_are_given_as_their_readers_describe_them(database_url: str) -> None:
    """The Admin form is drawn from this, and a store's settings are checked against it: what a
    kind of store needs to know is written once, by the collector's reader for it."""
    with TestClient(create_app(database_url)) as client:
        kinds = {kind["kind"]: kind for kind in client.get("/api/source-kinds").json()}

    assert sorted(kinds) == ["manual", "sap_commerce", "shopify", "sitemap"]
    # A store entered by hand is disktracker's own kind: never collected, nothing to set.
    assert kinds["manual"] == {
        "kind": "manual",
        "label": "Entered by hand",
        "collected": False,
        "page_test": False,
        "groups": [],
        "settings": [],
    }
    shopify = kinds["shopify"]
    assert (shopify["label"], shopify["collected"], shopify["page_test"]) == (
        "Shopify",
        True,
        False,
    )
    assert [
        (setting["name"], setting["type"], setting["required"]) for setting in shopify["settings"]
    ] == [
        ("collections", "list", True),
        ("free_shipping", "flag", False),
    ]
    sitemap = kinds["sitemap"]
    assert sitemap["page_test"] is True
    assert sitemap["groups"] == [
        {
            "name": "data",
            "label": "Pages that list several products",
            "help": "For a store whose page covers a whole family of drives and carries them as"
            " JSON inside a script. Left blank, each page is one product, read from its own"
            " price markup.",
        }
    ]
    # Every setting a sitemap store is saved with is one its kind describes.
    described = [setting["name"] for setting in sitemap["settings"]]
    assert described == [
        *("sitemap_path", "product_path_pattern", "free_shipping_marker"),
        *NO_EMBEDDED_DATA,
    ]


@pytest.mark.parametrize(
    ("kind", "settings", "field", "message"),
    [
        ("shopify", {"collections": "hard-drives"}, "collections", "Enter a list."),
        (
            "shopify",
            {"collections": ["all"], "free_shipping": "yes"},
            "free_shipping",
            "Choose yes or no.",
        ),
        ("shopify", {"collections": [""]}, "collections", "Enter at least one."),
        ("sitemap", {"sitemap_path": 5}, "sitemap_path", "Enter text."),
        # What each complaint says, since it is shown on the setting as it is.
        ("sap_commerce", {"api_url": "https://api.wd.test", "site": ""}, "site", "Enter this."),
        ("sitemap", {"sitemap_path": "sitemap.xml"}, "sitemap_path", "Start it with /."),
        (
            "sitemap",
            {**EMBEDDED_DATA, "data_model_field": ""},
            "data_model_field",
            "Say which this is: the settings beside it need it.",
        ),
        (
            "sitemap",
            {**EMBEDDED_DATA, "data_pattern": "models = "},
            "data_pattern",
            "Put a group, ( ), around the data.",
        ),
        (
            "sitemap",
            {"product_path_pattern": "(unclosed"},
            "product_path_pattern",
            "Enter a regular expression (missing ), unterminated subpattern at position 0).",
        ),
        (
            "shopify",
            {"collections": ["all"], "site": "us"},
            "site",
            "This kind of store has no such setting.",
        ),
    ],
)
def test_a_setting_of_the_wrong_sort_is_refused(
    database_url: str, kind: str, settings: dict[str, Any], field: str, message: str
) -> None:
    with TestClient(create_app(database_url)) as client:
        refused = client.post("/api/sources", json=source_input(kind=kind, settings=settings))

    assert refused.status_code == 422
    assert [(issue["loc"][-1], issue["msg"]) for issue in refused.json()["detail"]] == [
        (field, message)
    ]


def test_a_kind_of_store_nobody_reads_is_refused(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        refused = client.post("/api/sources", json=source_input(kind="magento"))

    assert refused.status_code == 422
    assert refused.json()["detail"][0]["loc"] == ["body", "kind"]
