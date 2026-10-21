"""A drive made on its own, before any price of it: kept with what it is given, found where drives
are managed and looked up, and refused under an MPN that already identifies one, however the two
requests fall."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from test_api import entered, post, price_payload
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
        detail = client.get(f"/api/drives/{drive['id']}").json()
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
    assert (detail["drive"], detail["offers"]) == (drive, [])
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
        every = client.get("/api/catalog-drives").json()
        by_mpn = client.get("/api/catalog-drives", params={"q": "ST18000"}).json()
        by_alias = client.get("/api/catalog-drives", params={"q": "0xyz18"}).json()
        needing = client.get("/api/catalog-drives", params={"issue": "unknown_specifications"})

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
        every = client.get("/api/catalog-drives").json()

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
        mpns = [row["drive"]["mpn"] for row in client.get("/api/catalog-drives").json()["items"]]

    assert same_mpn and same_alias
    assert [response.status_code for response in (as_mpn, as_alias)] == [409, 409]
    assert sorted(mpns) == ["ST18000NM000J", "ST8000VN004"]
