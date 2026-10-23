"""The stores offers are collected from: entered, checked, scheduled and removed."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from api_calls import (
    entered,
    post,
    price_payload,
    saved_offer,
    scraped_payload,
    source_input,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text


def test_the_western_digital_store_is_a_store(subject: TestClient) -> None:
    saved = post(
        subject, "/api/prices", entered(subject, price_payload(store="westerndigital", seller=""))
    )
    [offer] = subject.get("/api/offers").json()

    assert saved.status_code == 201, saved.text
    assert offer["store"] == "westerndigital"


def test_every_store_is_a_source_and_offers_are_recorded_under_and_named_by_one(
    subject: TestClient,
) -> None:
    by_hand = subject.post("/api/sources", json={"name": "Server Orbit!", "kind": "manual"})
    unknown = post(
        subject, "/api/prices", entered(subject, price_payload(store="nowhere", seller=""))
    )
    recorded = post(
        subject, "/api/prices", entered(subject, price_payload(store="serverorbit", seller=""))
    )
    offer = saved_offer(subject, recorded)
    due_now = subject.get("/api/sources", params={"due": True}).json()
    no_stores = subject.get("/api/stores")

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


def names(sources: list[dict[str, Any]]) -> set[str]:
    return {source["name"] for source in sources}


def test_sources_are_added_listed_and_edited_with_their_next_scheduled_run(
    subject: TestClient,
) -> None:
    before = datetime.now(UTC)
    assert names(subject.get("/api/sources").json()) == set(SEEDED_SOURCES)
    added = subject.post("/api/sources", json=source_input())
    assert added.status_code == 201, added.text
    source = added.json()
    edited = subject.put(
        f"/api/sources/{source['id']}",
        json=source_input(
            schedule="30 */6 * * *", enabled=False, transport="browser", basis="permission"
        ),
    )
    listed = subject.get("/api/sources").json()

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
    subject: TestClient,
) -> None:
    now = datetime.now(UTC)
    source = subject.post("/api/sources", json=source_input()).json()
    subject.post("/api/sources", json=source_input(name="Old Run"))
    never_run = due(subject)
    report_run_of(subject, "serverorbit", now)
    report_run_of(subject, "oldrun", now - timedelta(days=2))
    # An older run of a source that has run since does not make it due.
    report_run_of(subject, "serverorbit", now - timedelta(days=2))
    after_runs = due(subject)
    listed = {entry["name"]: entry for entry in subject.get("/api/sources").json()}

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


def test_a_switched_off_source_is_due_only_when_asked_to_run_now(subject: TestClient) -> None:
    source = subject.post("/api/sources", json=source_input(enabled=False)).json()
    idle = due(subject)
    asked = subject.post(f"/api/sources/{source['id']}/run")
    queued = due(subject)
    report_run_of(subject, "serverorbit", datetime.now(UTC) - timedelta(hours=1))
    before_the_request = due(subject)
    report_run_of(subject, "serverorbit", datetime.now(UTC))
    after_the_request = due(subject)
    missing = subject.post(f"/api/sources/{uuid4()}/run")

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
    subject: TestClient,
) -> None:
    """Every refusal is the schema's (tests/unit/collector/test_schemas.py); this is where the
    form is told it is, without the kind a source is checked as."""
    refused = subject.post("/api/sources", json=source_input(schedule="nightly"))
    listed = subject.get("/api/sources").json()

    assert refused.status_code == 422
    assert [issue["loc"] for issue in refused.json()["detail"]] == [["body", "schedule"]]
    assert names(listed) == set(SEEDED_SOURCES)


def test_source_names_and_keys_are_unique_and_only_existing_sources_can_be_edited(
    subject: TestClient,
) -> None:
    subject.post("/api/sources", json=source_input())
    other = subject.post("/api/sources", json=source_input(name="Elsewhere")).json()
    duplicate = subject.post("/api/sources", json=source_input(schedule="0 4 * * *"))
    same_key = subject.post("/api/sources", json=source_input(name="Server-Orbit"))
    renamed_onto = subject.put(f"/api/sources/{other['id']}", json=source_input())
    missing = subject.put(f"/api/sources/{uuid4()}", json=source_input(name="Nowhere"))

    assert [response.status_code for response in (duplicate, same_key, renamed_onto, missing)] == [
        409, 409, 409, 404,
    ]  # fmt: skip


def test_a_source_is_always_given_with_the_settings_its_kind_has_now(
    subject: TestClient, database_url: str
) -> None:
    """A source saved before a setting existed, or with one since dropped, reads as if saved
    today, so the collector never has to guess a default."""
    saved_long_ago = {"product_path_pattern": "-p/", "title_prefix": "Old Store - "}
    source = subject.post("/api/sources", json=source_input(kind="sitemap", settings={})).json()
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE sources SET settings = CAST(:settings AS jsonb) WHERE id = :id"),
            {"settings": json.dumps(saved_long_ago), "id": source["id"]},
        )
    engine.dispose()
    listed = subject.get("/api/sources").json()
    due_now = subject.get("/api/sources", params={"due": True}).json()

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


def test_a_setting_that_does_not_fit_is_refused_where_the_form_shows_it(
    subject: TestClient,
) -> None:
    """In the form's words, not the validator's."""
    refused = subject.post("/api/sources", json=source_input(settings={"collections": []}))
    unrooted = subject.post(
        "/api/sources",
        json=source_input(kind="sitemap", settings={"sitemap_path": "sitemap.xml"}),
    )
    api_url = subject.post(
        "/api/sources", json=source_input(kind="sap_commerce", settings={"site": "us"})
    )

    assert [response.status_code for response in (refused, unrooted, api_url)] == [422] * 3
    assert [
        (issue["loc"], issue["msg"])
        for response in (refused, unrooted, api_url)
        for issue in response.json()["detail"]
    ] == [
        (["body", "settings", "collections"], "Enter at least one."),
        (["body", "settings", "sitemap_path"], "Start it with /."),
        (["body", "settings", "api_url"], "Enter this."),
    ]


def test_permission_taken_away_while_robots_txt_is_ignored_is_refused_not_undone(
    subject: TestClient,
) -> None:
    """Who may ignore robots.txt is the schema's (tests/unit/collector/test_schemas.py)."""
    permitted = source_input(name="DirectMacro", basis="permission", obey_robots=False)
    source_id = subject.post("/api/sources", json=permitted).json()["id"]
    withdrawn = subject.put(f"/api/sources/{source_id}", json={**permitted, "basis": "terms_allow"})
    kept = [s for s in subject.get("/api/sources").json() if s["id"] == source_id]
    restored = subject.put(
        f"/api/sources/{source_id}",
        json={**permitted, "basis": "terms_allow", "obey_robots": True},
    )

    assert withdrawn.status_code == 422
    assert [issue["loc"] for issue in withdrawn.json()["detail"]] == [["body", "obey_robots"]]
    assert [(s["basis"], s["obey_robots"]) for s in kept] == [("permission", False)]
    assert restored.status_code == 200, restored.text
    assert (restored.json()["basis"], restored.json()["obey_robots"]) == ("terms_allow", True)


def test_a_source_with_offers_or_queued_offers_is_kept_and_so_is_other(subject: TestClient) -> None:
    sources = {source["key"]: source["id"] for source in subject.get("/api/sources").json()}
    post(
        subject,
        "/api/prices",
        entered(subject, price_payload(store="serverpartdeals", seller="")),
    )
    post(subject, "/api/ingestions", scraped_payload(store="goharddrive", mpn=None))
    refused = {
        key: subject.delete(f"/api/sources/{sources[key]}")
        for key in ("serverpartdeals", "goharddrive", "other")
    }
    listed = subject.get("/api/sources").json()

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


def test_a_source_keeps_the_key_it_was_created_with_when_renamed(subject: TestClient) -> None:
    source = subject.post("/api/sources", json=source_input()).json()
    renamed = subject.put(
        f"/api/sources/{source['id']}", json=source_input(name="Orbit Refurbished")
    ).json()

    assert (renamed["name"], renamed["key"]) == ("Orbit Refurbished", "serverorbit")


def test_the_kinds_of_store_are_given_as_their_settings_describe_them(subject: TestClient) -> None:
    """The Admin form is drawn from this; how each kind is described is its settings model's
    (tests/unit/collector/test_schemas.py)."""
    kinds = {kind["kind"]: kind for kind in subject.get("/api/source-kinds").json()}

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


def test_a_kind_of_store_nobody_reads_is_refused(subject: TestClient) -> None:
    refused = subject.post("/api/sources", json=source_input(kind="magento"))

    assert refused.status_code == 422
    assert refused.json()["detail"][0]["loc"] == ["body", "kind"]
