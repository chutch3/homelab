"""Taking in a page as collected: one request per observation, answered with one outcome, its
save key answering it again as it was. A price of an offer already known, a recheck among them,
is not ingested: it gives no new evidence of what the page is."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from api_calls import (
    collected_payload,
    entered,
    held_reasons,
    match,
    post,
    price_payload,
    saved_offer,
    scraped_payload,
    with_history,
)
from fastapi.testclient import TestClient


def test_a_collected_page_is_taken_in_once_whatever_times_it_is_sent(subject: TestClient) -> None:
    key = str(uuid4())
    first = post(subject, "/api/ingestions", scraped_payload(), key)
    again = post(subject, "/api/ingestions", scraped_payload(), key)
    queued = post(subject, "/api/ingestions", scraped_payload(mpn=None, url="https://spd.test/x"))
    prices = subject.get("/api/prices", params={"offer_id": first.json()["offer_id"]}).json()

    assert (first.status_code, first.json()["status"]) == (201, "recorded")
    assert (again.status_code, again.json()) == (201, first.json())
    assert (queued.status_code, queued.json()["status"]) == (202, "queued")
    assert prices["total"] == 1


@pytest.mark.parametrize(
    "fields",
    [
        {"offer_id": "11111111-1111-4111-8111-111111111111"},
        {"provenance": "collected"},
        {"on_unmatched": "queue"},
        {"url": None},
        {"title": None},
    ],
    ids=["named offer", "provenance", "review policy", "no page", "no title"],
)
def test_only_a_page_as_collected_is_taken_in(subject: TestClient, fields: dict[str, Any]) -> None:
    """Every page taken in is collected, and waits for review when it cannot be matched, which
    needs the page and title a reviewer is shown."""
    refused = post(subject, "/api/ingestions", {**scraped_payload(), **fields})
    kept = subject.get("/api/offers").json()

    assert refused.status_code == 422, refused.text
    assert kept == []


def test_a_collected_observation_of_a_described_offer_is_not_a_price(subject: TestClient) -> None:
    refused = post(subject, "/api/prices", {**scraped_payload(), "provenance": "collected"})

    assert refused.status_code == 422
    assert "/api/ingestions" in refused.text


def test_a_page_that_also_lists_its_own_mpn_among_its_others_makes_one_drive(
    subject: TestClient,
) -> None:
    taken = post(subject, "/api/ingestions", scraped_payload(
        mpn="OWNALIAS", aliases=["OWNALIAS", "0OTHER"], title="Drive 18TB",
    ))  # fmt: skip
    drive = subject.get(f"/api/offers/{taken.json()['offer_id']}").json()["drive"]

    assert (taken.status_code, taken.json()["status"]) == (201, "recorded"), taken.text
    assert (drive["mpn"], drive["aliases"]) == ("OWNALIAS", ["0OTHER"])


def test_a_sold_out_scraped_offer_records_only_that_it_is_out_of_stock(
    subject: TestClient,
) -> None:
    placeholder = {"in_stock": False, "item_price_cents": 1_000_000}
    unseen = post(subject, "/api/ingestions", scraped_payload(**placeholder))
    nothing = subject.get("/api/offers").json()
    post(subject, "/api/ingestions", scraped_payload())
    sold_out = post(
        subject,
        "/api/ingestions",
        scraped_payload(**placeholder, observed_at="2026-09-22T12:00:00Z"),
    )
    [offer] = subject.get("/api/offers").json()

    # Never seen in stock, it has no real price to track yet.
    assert (unseen.status_code, unseen.json()["status"], nothing) == (200, "ignored", [])
    assert sold_out.json()["status"] == "recorded"
    # Sold out, it keeps the price it last had in stock: the store's sold-out price is ignored.
    assert (offer["latest"]["in_stock"], offer["latest"]["item_price_cents"]) == (False, 36999)
    assert offer["last_checked_at"] == "2026-09-22T12:00:00Z"


def test_a_scraped_offer_with_an_mpn_and_condition_is_recorded_as_a_sourced_price(
    subject: TestClient,
) -> None:
    result = post(subject, "/api/ingestions", scraped_payload())
    assert result.status_code == 201, result.text
    assert result.json()["status"] == "recorded"
    [offer] = subject.get("/api/offers").json()
    assert result.json()["offer_id"] == offer["id"]
    assert (offer["mpn"], offer["store"], offer["condition"]) == (
        "ST18000NM000J",
        "serverpartdeals",
        "manufacturer_recertified",
    )
    assert offer["latest"]["item_price_cents"] == 36999
    assert offer["latest"]["provenance"] == "collected"
    manual = saved_offer(
        subject,
        post(subject, "/api/prices", entered(subject, price_payload(seller="Manual shop"))),
    )
    assert manual["latest"]["provenance"] == "manual"


def test_scraped_offers_that_cannot_be_matched_wait_in_the_review_queue(
    subject: TestClient,
) -> None:
    base = "https://www.serverpartdeals.com/products/"
    first = post(subject, "/api/ingestions", scraped_payload(mpn=None, url=base + "mystery"))
    assert first.status_code == 202, first.text
    assert first.json()["status"] == "queued"
    again = post(
        subject,
        "/api/ingestions",
        scraped_payload(
            mpn=None,
            url=base + "mystery",
            item_price_cents=35999,
            observed_at="2026-09-22T12:00:00Z",
        ),
    )
    assert again.json()["review_item_id"] == first.json()["review_item_id"]
    post(subject, "/api/ingestions", scraped_payload(url=base + "odd-condition", condition=None))
    post(subject, "/api/ingestions", scraped_payload())
    post(
        subject,
        "/api/ingestions",
        scraped_payload(
            url=base + "wrong-capacity",
            seller="x",
            capacity_gb=20000,
            title="Seagate Exos X18 ST18000NM000J 20TB",
        ),
    )
    post(
        subject,
        "/api/ingestions",
        scraped_payload(url=base + "new-drive", mpn="ST20000NM007D", capacity_gb=None),
    )
    queue = {item["url"]: item for item in subject.get("/api/review-items").json()}
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
    assert len(subject.get("/api/offers").json()) == 1


def test_an_offer_whose_page_comes_to_be_doubted_is_held_out_of_every_report_until_settled(
    subject: TestClient,
) -> None:
    """Recorded, then read again as several drives: it waits for a person, and until then it is
    in no ranking, no distribution and no trend, though it and its prices are kept and listed
    where offers are managed. Said to be what it was, it counts again."""
    now = datetime.now(UTC)
    page = scraped_payload(url="https://www.serverpartdeals.com/products/exos")
    for days, item in ((40.5, 37999), (0.001, 36999)):
        recorded = post(
            subject,
            "/api/ingestions",
            {
                **page,
                "item_price_cents": item,
                "observed_at": (now - timedelta(days=days)).isoformat(),
            },
        )
        assert recorded.status_code == 201, recorded.text
    offer_id = recorded.json()["offer_id"]

    def reports() -> dict[str, Any]:
        return {
            "drives": subject.get("/api/reports/market").json()["total"],
            "lowest": subject.get("/api/reports/market").json()["lowest"]["unit"],
            "today": len(subject.get("/api/reports/prices-today").json()),
            "trend": subject.get("/api/trends", params={"days": 30}).json()["market"]["counted"],
        }

    counted = reports()
    queued = post(subject, "/api/ingestions", {
        **page, "title": "Seagate Exos X18 ST18000NM000J 18TB Recertified 4-pack",
        "observed_at": now.isoformat(),
    })  # fmt: skip
    held = reports()
    managed = {o["id"]: o["doubt"] for o in subject.get("/api/offers").json()}
    kept = len(subject.get(f"/api/offers/{offer_id}").json()["observations"])
    decided = subject.put(
        f"/api/review-items/{queued.json()['review_item_id']}/decision",
        json=match(subject, "ST18000NM000J", "manufacturer_recertified"),
    )
    settled = reports()
    managed_after = {o["id"]: o["doubt"] for o in subject.get("/api/offers").json()}

    assert counted == {"drives": 1, "lowest": [offer_id], "today": 1, "trend": 1}
    assert queued.json()["status"] == "queued"
    assert held == {"drives": 0, "lowest": [], "today": 0, "trend": 0}
    assert (managed, kept) == ({offer_id: "not_a_single_drive"}, 2)
    assert (decided.status_code, decided.json()["offer_id"]) == (200, offer_id)
    assert settled == counted
    assert managed_after == {offer_id: None}


def test_a_collected_offer_no_single_drive_could_be_waits_for_a_person_to_say_what_it_is(
    subject: TestClient,
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
    # Under any ceiling, but its own title, read past its part number, says 3.2TB.
    misread = scraped_payload(
        url=base + "misread", mpn="P09094-H21", condition="refurbished",
        title="HPE P09094-H213.2TB SAS 12GBPS Smart Carrier", capacity_gb=213200,
    )  # fmt: skip
    queued = [post(subject, "/api/ingestions", entry) for entry in (bundle, huge, misread)]
    queue = {item["url"]: item["reason"] for item in subject.get("/api/review-items").json()}
    # A person says what the second one is: a 960 GB drive, made as one first.
    decided = subject.put(
        f"/api/review-items/{queued[1].json()['review_item_id']}/decision",
        json=match(subject, "KPM7XVUG960G", "new", 960),
    )
    later = post(subject, "/api/ingestions", {**huge, "observed_at": "2026-09-22T12:00:00Z"})
    # Entered by hand, it is what the person says it is.
    by_hand = post(
        subject,
        "/api/prices",
        entered(
            subject,
            price_payload(mpn="R0P90A", title="HPE R0P90A 48TB (8x6) 6-pack", capacity_gb=48000),
        ),
    )

    assert [answer.json()["status"] for answer in queued] == ["queued"] * 3
    assert queue == {
        base + "bundle": "not_a_single_drive",
        base + "kioxia": "implausible_capacity",
        base + "misread": "implausible_capacity",
    }
    assert decided.status_code == 200, decided.text
    assert (later.status_code, later.json()["status"]) == (201, "recorded")
    assert by_hand.status_code == 201, by_hand.text


def test_a_queued_listing_leaves_the_review_queue_once_a_later_scrape_of_it_is_recorded(
    subject: TestClient,
) -> None:
    """Read as it was queued, and recorded: no longer waiting. Read with an MPN it lacked, it is
    another listing, and the one that lacked it still waits: saying more is no evidence that the
    two are one product."""
    base = "https://www.serverpartdeals.com/products/"
    queued = post(
        subject, "/api/ingestions", scraped_payload(url=base + "mystery", title="Exos 4-pack")
    )
    post(subject, "/api/ingestions", scraped_payload(mpn=None, url=base + "another"))
    fuller = post(subject, "/api/ingestions", scraped_payload(url=base + "another"))
    later = post(subject, "/api/ingestions", scraped_payload(url=base + "mystery"))
    waiting = [(item["url"], item["mpn"]) for item in subject.get("/api/review-items").json()]

    assert queued.json()["status"] == "queued"
    assert [fuller.status_code, later.status_code] == [201, 201]
    assert waiting == [(base + "another", None)]


def test_a_scraped_offer_names_the_other_mpns_its_drive_goes_by(subject: TestClient) -> None:
    """MPNs no drive goes by yet become its drive's; a page that later uses one is of that drive."""
    base = "https://www.serverpartdeals.com/products/"
    maker = post(subject, "/api/ingestions", scraped_payload(
        url=base + "bare", mpn="WUH721816AL5205", title="WD Ultrastar WUH721816AL5205 16TB",
        aliases=["0hnhwc"], capacity_gb=16000, condition="refurbished",
    ))  # fmt: skip
    oem = post(subject, "/api/ingestions", scraped_payload(
        url=base + "dell-g14", mpn="0HNHWC", capacity_gb=16000, condition="new",
        title="Dell 0HNHWC 16TB SAS",
    ))  # fmt: skip
    offers = {o["id"]: o for o in subject.get("/api/offers").json()}

    assert [maker.status_code, oem.status_code] == [201, 201]
    assert offers[maker.json()["offer_id"]]["drive"]["aliases"] == ["0HNHWC"]
    assert offers[oem.json()["offer_id"]]["drive"]["mpn"] == "WUH721816AL5205"


@pytest.mark.parametrize("claimed_as", ["its own MPN", "another of its MPNs"])
def test_a_scraped_offer_naming_an_mpn_another_drive_goes_by_waits_whole_for_a_person(
    subject: TestClient, claimed_as: str
) -> None:
    """No drive is merged, and nothing the page said is taken, not even its price for an offer
    already recorded: what it said waits for a person, with the MPN and the drive it is."""
    page = scraped_payload(
        url="https://www.serverpartdeals.com/products/other", mpn="ST16000NM000J",
        title="Seagate Exos ST16000NM000J 16TB", capacity_gb=16000,
    )  # fmt: skip
    if claimed_as == "its own MPN":
        owner = saved_offer(
            subject,
            post(
                subject,
                "/api/prices",
                entered(subject, price_payload(mpn="0XYZ", capacity_gb=18000)),
            ),
        )
    else:
        owner = saved_offer(
            subject,
            post(subject, "/api/prices", entered(subject, price_payload(mpn="ST18000NM000J"))),
        )
        subject.post(f"/api/drives/{owner['drive']['id']}/aliases", json={"mpn": "0XYZ"})
    recorded = post(subject, "/api/ingestions", page).json()
    conflicting = post(subject, "/api/ingestions", {
        **page, "aliases": ["0XYZ"], "brand": "Seagate", "item_price_cents": 30000,
        "observed_at": "2026-09-22T12:00:00Z",
    })  # fmt: skip
    offer = subject.get(f"/api/offers/{recorded['offer_id']}").json()
    [item] = subject.get("/api/review-items").json()
    drives = {o["drive"]["mpn"] for o in subject.get("/api/offers").json()}

    assert conflicting.json()["status"] == "queued"
    assert [p["item_price_cents"] for p in offer["observations"]] == [36999]
    assert (offer["drive"]["brand"], offer["drive"]["aliases"]) == (None, [])
    assert (item["reason"], item["aliases"], item["conflict_mpn"]) == (
        "alias_conflict",
        ["0XYZ"],
        "0XYZ",
    )
    assert item["conflict_drive_id"] == owner["drive"]["id"]
    assert drives == {owner["drive"]["mpn"], "ST16000NM000J"}


def test_a_scraped_offer_names_its_drive_s_brand_until_one_is_known(subject: TestClient) -> None:
    manual = post(
        subject,
        "/api/prices",
        entered(subject, price_payload(mpn="WD120EFBX", capacity_gb=12000)),
    )
    assert saved_offer(subject, manual)["drive"]["brand"] is None
    first = post(subject, "/api/ingestions", scraped_payload(brand="Seagate"))
    later = post(
        subject,
        "/api/ingestions",
        scraped_payload(brand="Dell", item_price_cents=35999, observed_at="2026-09-23T12:00:00Z"),
    )
    unnamed = post(
        subject,
        "/api/ingestions",
        scraped_payload(
            mpn="WD120EFBX",
            capacity_gb=12000,
            url="https://spd.test/wd",
            title="WD Red Plus WD120EFBX 12TB",
        ),
    )
    brands = {o["mpn"]: o["drive"]["brand"] for o in subject.get("/api/offers").json()}
    too_long = post(subject, "/api/ingestions", scraped_payload(brand="x" * 61))

    assert (first.status_code, later.status_code, unnamed.status_code) == (201, 201, 201)
    assert brands == {"ST18000NM000J": "Seagate", "WD120EFBX": None}
    assert too_long.status_code == 422


def test_a_scraped_offer_fills_in_specifications_nobody_has_entered(subject: TestClient) -> None:
    first = post(
        subject,
        "/api/ingestions",
        scraped_payload(
            specifications={"media_type": "hdd", "form_factor": "3_5", "interface": "sas"}
        ),
    )
    assert first.status_code == 201, first.text
    drive = subject.get(f"/api/offers/{first.json()['offer_id']}").json()["drive"]
    assert drive["specifications"] == {
        "media_type": "hdd",
        "form_factor": "3_5",
        "interface": "sas",
        "recording_type": "unknown",
        "intended_use": [],
    }
    entered = {**drive["specifications"], "interface": "sata", "intended_use": ["nas"]}
    subject.patch(
        f"/api/drives/{drive['id']}",
        json={"capacity_gb": 18000, "specifications": entered},
    )

    later = post(
        subject,
        "/api/ingestions",
        scraped_payload(
            item_price_cents=35999,
            observed_at="2026-09-23T12:00:00Z",
            specifications={"interface": "sas", "recording_type": "cmr"},
        ),
    )

    assert later.status_code == 201, later.text
    after = subject.get(f"/api/offers/{later.json()['offer_id']}").json()["drive"]
    assert after["specifications"] == {**entered, "recording_type": "cmr"}


def test_a_retry_replays_whatever_was_done_whether_recorded_queued_or_ignored(
    subject: TestClient,
) -> None:
    unmatched = collected_payload(mpn=None)
    sold_out = collected_payload(in_stock=False, seller="never seen")
    answers = []
    for payload in (collected_payload(), unmatched, sold_out):
        key = str(uuid4())
        first, retry = (post(subject, "/api/ingestions", payload, key) for _ in range(2))
        changed = post(subject, "/api/ingestions", {**payload, "item_price_cents": 1}, key)
        answers.append((first.status_code, first.json()["status"], retry.status_code))
        assert retry.json() == first.json()
        assert changed.status_code == 409
    queue = subject.get("/api/review-items").json()
    [offer] = with_history(subject)

    assert answers == [(201, "recorded", 201), (202, "queued", 202), (200, "ignored", 200)]
    assert len(queue) == 1
    assert len(offer["observations"]) == 1


def test_a_hold_is_released_only_by_fresh_evidence_of_the_offer_it_is_on(
    subject: TestClient, database_url: str
) -> None:
    """One store page, two offers of it: new and refurbished. Read as several drives, both are
    held. A clean collection of the new one releases the new one alone, and leaves what waits for
    review of the other. A price saved by hand, or named by the offer it is for, or a page
    ignored, says nothing new of what the offer is: each leaves its hold."""
    now = datetime.now(UTC)
    page = scraped_payload(url="https://www.serverpartdeals.com/products/exos")
    at = lambda days: (now - timedelta(days=days)).isoformat()
    new = post(subject, "/api/ingestions", {**page, "condition": "new", "observed_at": at(2)})
    refurbished = post(
        subject, "/api/ingestions", {**page, "condition": "refurbished", "observed_at": at(2)}
    )
    ids = {"new": new.json()["offer_id"], "refurbished": refurbished.json()["offer_id"]}
    bundle = "Seagate Exos X18 ST18000NM000J 18TB 4-pack"
    post(
        subject,
        "/api/ingestions",
        {**page, "condition": "new", "title": bundle, "observed_at": at(1.5)},
    )
    queued = post(
        subject,
        "/api/ingestions",
        {**page, "condition": "refurbished", "title": bundle, "observed_at": at(1.4)},
    )
    both_held = held_reasons(database_url)

    by_hand = post(
        subject,
        "/api/prices",
        entered(
            subject,
            {"offer_id": ids["refurbished"], "item_price_cents": 30000, "observed_at": at(1.3)},
        ),
    )
    recheck = post(
        subject,
        "/api/prices",
        entered(
            subject,
            {
                "offer_id": ids["new"],
                "provenance": "collected",
                "item_price_cents": 35000,
                "observed_at": at(1.2),
            },
        ),
    )
    after_named = held_reasons(database_url)

    clean = post(
        subject,
        "/api/ingestions",
        {**page, "condition": "new", "item_price_cents": 34000, "observed_at": at(1)},
    )
    after_clean = held_reasons(database_url)
    waiting = [
        (item["condition"], item["reason"]) for item in subject.get("/api/review-items").json()
    ]

    ignored = subject.put(
        f"/api/review-items/{queued.json()['review_item_id']}/decision",
        json={"decision": "ignore"},
    )
    after_ignore = held_reasons(database_url)

    assert both_held == {"new": "not_a_single_drive", "refurbished": "not_a_single_drive"}
    assert [r.json()["status"] for r in (by_hand, recheck, clean)] == ["recorded"] * 3
    # Recorded, both prices, and still held.
    assert [r.json()["price_id"] is not None for r in (by_hand, recheck)] == [True, True]
    assert after_named == both_held
    assert after_clean == {"new": None, "refurbished": "not_a_single_drive"}
    assert waiting == [("refurbished", "not_a_single_drive")]
    assert ignored.status_code == 200, ignored.text
    assert after_ignore == after_clean
