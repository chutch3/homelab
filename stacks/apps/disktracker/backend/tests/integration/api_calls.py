"""How the integration tests speak to the API: the requests they make, and what they send."""

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine, text


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


# What a price says of a drive's offer; the rest of a description is the drive's.
DRIVE_FIELDS = ("mpn", "capacity_gb", "brand", "specifications")


def drive_of(client: TestClient, mpn: str, capacity_gb: int | None = None, **drive: Any) -> str:
    """The drive that goes by this MPN, or one made under it, as a person finds or makes one
    before saying anything of it."""
    made = client.post("/api/drives", json={"mpn": mpn, "capacity_gb": capacity_gb, **drive})
    if made.status_code == 201:
        made_id: str = made.json()["id"]
        return made_id
    assert made.status_code in (409, 422), made.text
    [found] = client.get("/api/drives", params={"mpn": mpn}).json()["items"]
    drive_id = found["drive"]["id"]
    found_id: str = drive_id
    return found_id


def entered(client: TestClient, described: dict[str, Any]) -> dict[str, Any]:
    """A price described by its drive's MPN, as a person enters it: the drive found by that MPN,
    or made first, and the price then of that drive. One that names its offer is as it is."""
    if "offer_id" in described:
        return described
    drive = {key: described[key] for key in DRIVE_FIELDS if described.get(key) is not None}
    price = {key: value for key, value in described.items() if key not in DRIVE_FIELDS}
    return {"drive_id": drive_of(client, **drive), **price}


def match(
    client: TestClient, mpn: str, condition: str, capacity_gb: int | None = None
) -> dict[str, Any]:
    """A reviewer's decision that an item is the drive that goes by this MPN, found or made
    first, in this condition."""
    return {
        "decision": "match",
        "drive_id": drive_of(client, mpn, capacity_gb),
        "condition": condition,
    }


def scraped_payload(**fields: Any) -> dict[str, Any]:
    return {
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
        response = post(client, "/api/prices", entered(client, {**payload, **fields}))
        assert response.status_code == 201, response.text

    return record


def followed_drives(client: TestClient, now: datetime) -> Any:
    """Three drives priced all month, each checked just now. Returns the recorder for more."""
    record = priced_days_ago(client, now)
    for mpn, item in [("ST10000NM001G", 10000), ("ST10000NM002G", 20000), ("ST10000NM003G", 30000)]:
        record(mpn, item, 40.5)
        record(mpn, item, 0.001)
    return record


def collected_payload(**fields: Any) -> dict[str, Any]:
    """A price as a collector submits it: under the store it read, and to be queued for review
    when it cannot be matched."""
    return scraped_payload(**fields)


def held_reasons(database_url: str) -> dict[str, str | None]:
    """Each offer's hold, by its condition."""
    engine = create_engine(database_url)
    with engine.connect() as connection:
        found = dict(
            connection.execute(text("SELECT condition, held_reason FROM listings")).tuples().all()
        )
    engine.dispose()
    return found
