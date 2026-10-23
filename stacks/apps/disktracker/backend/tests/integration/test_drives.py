"""A drive made on its own, before any price of it: kept with what it is given, found where drives
are managed and looked up, and refused under an MPN that already identifies one, however the two
requests fall."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from api_calls import entered, post, price_payload, saved_offer, scraped_payload
from fastapi.testclient import TestClient
from test_persistence import meanwhile

from disktracker.main import create_app

EXOS = {"mpn": "st18000nm000j", "capacity_gb": 18000}


def test_a_drive_is_made_with_what_it_is_given_and_kept_with_no_offer(database_url: str) -> None:
    with TestClient(create_app()) as client:
        made = client.post(
            "/api/drives",
            json={**EXOS, "brand": "Seagate", "specifications": {"interface": "sas"}},
        )
        drive = made.json()
        read = client.get(f"/api/drives/{drive['id']}").json()
        of_it = client.get("/api/offers", params={"drive_id": drive["id"]}).json()
        bare = client.post("/api/drives", json={"mpn": "WUH721212ALE6L4", "capacity_gb": 12000})

    assert made.status_code == 201, made.text
    assert drive == {
        "id": drive["id"],
        # As every MPN is kept: in capitals.
        "mpn": "ST18000NM000J",
        "capacity_gb": 18000,
        "brand": "Seagate",
        "specifications": {
            "media_type": "unknown", "form_factor": "unknown", "interface": "sas",
            "recording_type": "unknown", "intended_use": [],
        },
        "aliases": [],
    }  # fmt: skip
    assert (read, of_it) == (drive, [])
    assert bare.status_code == 201, bare.text
    assert (bare.json()["brand"], bare.json()["specifications"]["interface"]) == (None, "unknown")


def test_a_drive_with_no_offer_is_managed_and_looked_up_like_any_other(database_url: str) -> None:
    """Named by its MPN, with nothing to count and nothing in stock: after those that are."""
    with TestClient(create_app()) as client:
        post(
            client,
            "/api/prices",
            entered(
                client,
                price_payload(
                    mpn="ST16000NM001G",
                    capacity_gb=16000,
                    observed_at=datetime.now(UTC).isoformat(),
                ),
            ),
        )
        made = client.post("/api/drives", json=EXOS).json()
        client.post(f"/api/drives/{made['id']}/aliases", json={"mpn": "0XYZ18"})
        every = client.get("/api/reports/drive-inventory").json()
        by_mpn = client.get("/api/reports/drive-inventory", params={"q": "ST18000"}).json()
        by_alias = client.get("/api/reports/drive-inventory", params={"q": "0xyz18"}).json()
        needing = client.get(
            "/api/reports/drive-inventory", params={"issue": "unknown_specifications"}
        )

    assert [row["drive"]["mpn"] for row in every["items"]] == ["ST16000NM001G", "ST18000NM000J"]
    assert (every["total"], every["all"]) == (2, 2)
    assert every["items"][1] == {
        "drive": {**made, "aliases": ["0XYZ18"]},
        "title": "ST18000NM000J",
        "offers": 0,
        "issues": ["unknown_specifications"],
    }
    assert [row["drive"]["id"] for row in by_mpn["items"]] == [made["id"]]
    assert [row["drive"]["id"] for row in by_alias["items"]] == [made["id"]]
    assert needing.json()["issues"] == {"unknown_specifications": 2, "stale": 0}


def test_a_drive_is_refused_under_an_mpn_that_already_identifies_one(database_url: str) -> None:
    """A drive's own MPN or another of its MPNs: nothing is merged, and nothing changes."""
    with TestClient(create_app()) as client:
        first = client.post("/api/drives", json=EXOS).json()
        client.post(f"/api/drives/{first['id']}/aliases", json={"mpn": "0XYZ18"})
        again = client.post("/api/drives", json={**EXOS, "capacity_gb": 20000})
        alias = client.post("/api/drives", json={"mpn": "0xyz18", "capacity_gb": 18000})
        refused = client.post("/api/drives", json={"mpn": "ST1", "capacity_gb": 0})
        every = client.get("/api/reports/drive-inventory").json()

    assert (again.status_code, again.json()) == (
        409,
        {"detail": "ST18000NM000J already identifies a drive."},
    )
    assert (alias.status_code, alias.json()) == (
        409,
        {"detail": "0XYZ18 already identifies a drive."},
    )
    assert refused.status_code == 422
    assert [(row["drive"]["mpn"], row["drive"]["capacity_gb"]) for row in every["items"]] == [
        ("ST18000NM000J", 18000)
    ]


def test_a_drive_made_while_another_takes_its_mpn_is_refused_not_failed(database_url: str) -> None:
    """Whichever namespace the other took it in, the moment before this one is written."""
    other: Any = {}
    with TestClient(create_app()) as client:
        other = client.post("/api/drives", json={"mpn": "ST8000VN004", "capacity_gb": 8000}).json()
        with meanwhile(
            database_url,
            "INSERT INTO drives",
            "INSERT INTO drives (id, mpn, capacity_gb, specifications)"
            " VALUES (:id, 'ST18000NM000J', 18000, '{}')",
            id=uuid4(),
        ) as same_mpn:
            as_mpn = client.post("/api/drives", json=EXOS)
        with meanwhile(
            database_url,
            "INSERT INTO drives",
            "INSERT INTO mpn_aliases (alias, drive_id) VALUES ('ST10000NM001G', :drive)",
            drive=other["id"],
        ) as same_alias:
            as_alias = client.post(
                "/api/drives", json={"mpn": "ST10000NM001G", "capacity_gb": 10000}
            )
        mpns = [
            row["drive"]["mpn"]
            for row in client.get("/api/reports/drive-inventory").json()["items"]
        ]

    assert same_mpn and same_alias
    assert [response.status_code for response in (as_mpn, as_alias)] == [409, 409]
    assert sorted(mpns) == ["ST18000NM000J", "ST8000VN004"]


def test_a_drive_is_found_by_any_mpn_it_goes_by_or_by_words_any_name_of_it_has(
    database_url: str,
) -> None:
    """By an MPN exactly, as MPNs are kept: the drive that goes by it, as its own or another, or
    none. By words: every drive any of its names has them, those the words are an MPN of first,
    each named by its cheapest offer (else its MPN)."""
    with TestClient(create_app()) as client:
        post(client, "/api/prices", entered(client, price_payload(
            mpn="ST18000NM003D", capacity_gb=18000, title="Exos X20 18TB", item_price_cents=17000,
        )))  # fmt: skip
        made = client.post("/api/drives", json=EXOS).json()
        client.post(f"/api/drives/{made['id']}/aliases", json={"mpn": "0XYZ18"})

        def found(**query: Any) -> list[tuple[str, str]]:
            answer = client.get("/api/drives", params=query)
            assert answer.status_code == 200, answer.text
            return [(row["drive"]["mpn"], row["title"]) for row in answer.json()["items"]]

        by_mpn = found(mpn=" st18000nm000j ")
        by_alias = found(mpn="0xyz18")
        by_nothing = found(mpn="ST18000")
        by_words = found(q="st18000nm00")
        exact_first = found(q="ST18000NM000J")
        by_title = found(q="exos x20")
        paged = client.get("/api/drives", params={"q": "ST18000", "limit": 1}).json()
        refused = client.get("/api/drives").status_code

    assert by_mpn == by_alias == [("ST18000NM000J", "ST18000NM000J")]
    assert by_nothing == []
    assert by_words == [("ST18000NM000J", "ST18000NM000J"), ("ST18000NM003D", "Exos X20 18TB")]
    assert exact_first[0] == ("ST18000NM000J", "ST18000NM000J")
    assert by_title == [("ST18000NM003D", "Exos X20 18TB")]
    assert (paged["total"], len(paged["items"])) == (2, 1)
    # Neither an MPN nor words: no question asked.
    assert refused == 422


def test_replacing_a_drives_plain_specifications_updates_every_offer_for_that_mpn(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        offer = saved_offer(client, post(client, "/api/prices", entered(client, price_payload())))
        assert offer["drive"]["specifications"] == {
            "media_type": "unknown",
            "form_factor": "unknown",
            "interface": "unknown",
            "recording_type": "unknown",
            "intended_use": [],
        }
        post(client, "/api/prices", entered(client, price_payload(seller="Other seller")))
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
        drive = post(client, "/api/ingestions", scraped_payload(brand="Dell")).json()
        offer = client.get("/api/offers").json()[0]
        path = f"/api/drives/{offer['drive']['id']}"
        body = {"capacity_gb": 18000, "specifications": specifications}
        named = client.patch(path, json={**body, "brand": "  Seagate "})
        post(
            client,
            "/api/ingestions",
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
    """A price never says what a drive's capacity is: one that disagrees is refused where a drive
    is made (POST /drives) and queued where a page is taken in (POST /ingestions)."""
    with TestClient(create_app()) as client:
        first = saved_offer(client, post(client, "/api/prices", entered(client, price_payload())))
        assert first["capacity_gb"] == 18000
        assert first["drive"]["capacity_gb"] == 18000
        reused = post(
            client,
            "/api/prices",
            entered(client, price_payload(seller="Other seller", capacity_gb=None)),
        )
        assert saved_offer(client, reused)["capacity_gb"] == 18000
        assert saved_offer(client, reused)["latest"]["price_per_tb"] == "11.06"
        assert len(client.get("/api/offers").json()) == 2


def test_mpns_are_normalized_so_spacing_and_case_do_not_split_a_drive(database_url: str) -> None:
    with TestClient(create_app()) as client:
        first = saved_offer(
            client,
            post(client, "/api/prices", entered(client, price_payload(mpn=" st18000 nm000j "))),
        )
        assert first["mpn"] == "ST18000NM000J"
        second = saved_offer(
            client,
            post(client, "/api/prices", entered(client, price_payload(seller="Other seller"))),
        )
        assert second["drive"]["id"] == first["drive"]["id"]
        assert first["drive"]["aliases"] == []


def test_another_mpn_no_drive_goes_by_is_its_drives_and_routes_later_prices(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        canonical = saved_offer(
            client, post(client, "/api/prices", entered(client, price_payload(seller="Shop B")))
        )
        path = f"/api/drives/{canonical['drive']['id']}/aliases"
        added = client.post(path, json={"mpn": "st18000nm000j-2e3101"})
        later = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                entered(client, price_payload(mpn="ST18000NM000J-2E3101", seller="Shop A")),
            ),
        )
        missing = client.post(f"/api/drives/{uuid4()}/aliases", json={"mpn": "X"})

    assert added.status_code == 201, added.text
    assert added.json()["aliases"] == ["ST18000NM000J-2E3101"]
    assert (later["drive"]["id"], later["mpn"]) == (canonical["drive"]["id"], "ST18000NM000J")
    assert missing.status_code == 404


@pytest.mark.parametrize("taken_as", ["its own MPN", "another of its MPNs"])
def test_an_mpn_another_drive_goes_by_is_refused_naming_that_drive_and_nothing_merges(
    database_url: str, taken_as: str
) -> None:
    """Joining two drives is a merge, asked for as one (tests/integration/test_merge.py)."""
    with TestClient(create_app()) as client:
        owner = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                entered(client, price_payload(mpn="ST18000NM000J-2E3101", seller="Shop A")),
            ),
        )
        taken = "ST18000NM000J-2E3101"
        if taken_as == "another of its MPNs":
            client.post(f"/api/drives/{owner['drive']['id']}/aliases", json={"mpn": "0XYZ"})
            taken = "0XYZ"
        other = saved_offer(
            client, post(client, "/api/prices", entered(client, price_payload(seller="Shop B")))
        )
        refused = client.post(f"/api/drives/{other['drive']['id']}/aliases", json={"mpn": taken})
        itself = client.post(
            f"/api/drives/{other['drive']['id']}/aliases", json={"mpn": "ST18000NM000J"}
        )
        drives = {o["seller"]: o["drive"] for o in client.get("/api/offers").json()}

    assert (refused.status_code, refused.json()) == (
        409, {"detail": f"{taken} already identifies drive ST18000NM000J-2E3101."},
    )  # fmt: skip
    assert itself.status_code == 409
    assert drives["Shop A"]["id"] != drives["Shop B"]["id"]
    assert drives["Shop B"]["aliases"] == []


def test_small_drives_and_cards_are_tracked_in_whole_gigabytes(database_url: str) -> None:
    with TestClient(create_app()) as client:
        card = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                entered(
                    client,
                    price_payload(
                        mpn="SDSQXAA-128G", capacity_gb=128, item_price_cents=1999, shipping_cents=0
                    ),
                ),
            ),
        )
        tiny = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                entered(
                    client,
                    price_payload(
                        mpn="SDSQUA4-032G", capacity_gb=32, item_price_cents=599, shipping_cents=0
                    ),
                ),
            ),
        )

    assert (card["capacity_gb"], card["latest"]["price_per_tb"]) == (128, "156.17")
    assert (tiny["capacity_gb"], tiny["latest"]["price_per_tb"]) == (32, "187.19")


def test_a_drive_is_corrected_a_field_at_a_time(database_url: str) -> None:
    """What a correction leaves out stays as it was, down to each specification."""
    with TestClient(create_app()) as client:
        recorded = post(
            client,
            "/api/ingestions",
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
