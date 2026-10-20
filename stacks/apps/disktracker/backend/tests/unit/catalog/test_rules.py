from datetime import UTC, datetime
from typing import Any

import pytest

from disktracker.catalog.rules import (
    CapacityConflict,
    CapacityRequired,
    DecisionConflict,
    IdempotencyConflict,
    PriceRequired,
    as_decided,
    capacity_label,
    combined_offer,
    comparable_price,
    decided_again,
    doubt,
    fill_unknown,
    merge_plan,
    merged_drive,
    missing_detail,
    new_aliases,
    normalize_mpn,
    preview_verdict,
    queue_reason,
    queued_fields,
    replayed,
    source_key,
    unchanged,
    with_carried_price,
)
from disktracker.errors import MergeConflict

EARLIER = datetime(2026, 9, 21, 12, tzinfo=UTC)
LATER = datetime(2026, 9, 22, 12, tzinfo=UTC)
LATEST: dict[str, Any] = {
    "item_price_cents": 18900,
    "shipping_cents": 1000,
    "in_stock": True,
    "observed_at": EARLIER,
}


def price(**fields: Any) -> dict[str, Any]:
    return {"item_price_cents": 18900, "shipping_cents": 1000, "in_stock": True, **fields}


def test_same_price_shipping_and_stock_observed_later_is_unchanged() -> None:
    assert unchanged(price(), LATER, LATEST) is True


@pytest.mark.parametrize(
    "change",
    [{"item_price_cents": 17900}, {"shipping_cents": None}, {"in_stock": False}],
)
def test_any_difference_is_a_new_price(change: dict[str, Any]) -> None:
    assert unchanged(price(**change), LATER, LATEST) is False


def test_a_backdated_price_is_always_stored() -> None:
    assert unchanged(price(), datetime(2026, 9, 1, tzinfo=UTC), LATEST) is False


def test_the_first_price_is_never_unchanged() -> None:
    assert unchanged(price(), LATER, None) is False


def test_a_priced_entry_is_kept_as_is() -> None:
    assert with_carried_price(price(item_price_cents=17000), LATEST) == price(
        item_price_cents=17000
    )


def test_a_sold_out_check_without_a_price_keeps_the_last_price_and_shipping() -> None:
    sold_out = price(item_price_cents=None, shipping_cents=0, in_stock=False)
    assert with_carried_price(sold_out, LATEST) == price(in_stock=False)


def test_an_offer_with_no_price_yet_cannot_be_recorded_without_one() -> None:
    with pytest.raises(PriceRequired):
        with_carried_price(price(item_price_cents=None, in_stock=False), None)


def test_a_complete_offer_is_not_missing_anything() -> None:
    assert missing_detail("ST18000NM000J", "new") is None


def test_the_mpn_is_reported_before_the_condition() -> None:
    assert missing_detail(None, None) == "missing_mpn"
    assert missing_detail("ST18000NM000J", None) == "missing_condition"


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (CapacityConflict("x"), "capacity_conflict"),
        (CapacityRequired(), "missing_capacity"),
        (PriceRequired(), "missing_price"),
    ],
)
def test_queue_reason_for_a_price_that_could_not_be_recorded(error: Exception, reason: str) -> None:
    assert queue_reason(error) == reason


def test_new_aliases_skips_the_drives_own_mpn_and_existing_aliases() -> None:
    assert new_aliases(
        ["WUH721816AL5205", "0HNHWC", "0F38376", "0HNHWC"], "WUH721816AL5205", ["0F38376"]
    ) == ["0HNHWC"]


def test_merge_plan_combines_matching_offers_and_moves_the_rest() -> None:
    def offer(offer_id: str, seller: str, condition: str = "new") -> dict[str, Any]:
        return {"id": offer_id, "store": "ebay", "seller": seller, "condition": condition}

    variant = [offer("v1", "Shop A"), offer("v2", "Shop B"), offer("v3", "Shop B", "used")]
    drive = [offer("d1", "Shop B"), offer("d2", "Shop C")]
    assert merge_plan(variant, drive) == [("v1", None), ("v2", "d1"), ("v3", None)]


def test_found_specifications_fill_only_what_is_still_unknown() -> None:
    current = {
        "media_type": "hdd",
        "form_factor": "unknown",
        "interface": "sata",
        "recording_type": "unknown",
        "intended_use": [],
    }
    found = {
        "media_type": "ssd",
        "form_factor": "3_5",
        "interface": "sas",
        "recording_type": "unknown",
        "intended_use": ["enterprise"],
    }
    assert fill_unknown(current, found) == {
        "media_type": "hdd",
        "form_factor": "3_5",
        "interface": "sata",
        "recording_type": "unknown",
        "intended_use": ["enterprise"],
    }


@pytest.mark.parametrize(
    ("gigabytes", "label"),
    [(18000, "18 TB"), (1920, "1.92 TB"), (1000, "1 TB"), (960, "960 GB"), (32, "32 GB")],
)
def test_capacity_label_uses_terabytes_from_one_terabyte_up(gigabytes: int, label: str) -> None:
    assert capacity_label(gigabytes) == label


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ST18000NM000J", "ST18000NM000J"),
        (" st18000nm000j ", "ST18000NM000J"),
        ("ST18000 NM000J", "ST18000NM000J"),
        ("wuh721818ale6l4\t", "WUH721818ALE6L4"),
        ("ST18000NM000J-2E3101", "ST18000NM000J-2E3101"),
    ],
)
def test_normalize_mpn(raw: str, expected: str) -> None:
    assert normalize_mpn(raw) == expected


@pytest.mark.parametrize(
    ("item", "shipping", "capacity_gb", "expected"),
    [
        (18900, 1000, 18000, (19900, "11.06")),
        (100, 0, 8000, (100, "0.13")),
        (10000, 250, 10000, (10250, "10.25")),
        (0, 0, 10000, (0, "0.00")),
        (18900, None, 18000, (18900, "10.50")),
        (1999, 0, 128, (1999, "156.17")),
        (7499, 0, 960, (7499, "78.11")),
    ],
)
def test_comparable_price_is_per_decimal_terabyte(
    item: int, shipping: int | None, capacity_gb: int, expected: tuple[int, str]
) -> None:
    assert comparable_price(item, shipping, capacity_gb) == expected


def scraped(**fields: Any) -> dict[str, Any]:
    """An offer as the collector reads it from a store."""
    return {
        "title": "Seagate Exos X18 ST18000NM000J 18TB",
        "mpn": "ST18000NM000J",
        "condition": "new",
        "capacity_gb": 18000,
        "in_stock": True,
        **fields,
    }


@pytest.mark.parametrize(
    ("offer", "known", "verdict"),
    [
        (scraped(mpn=None), 18000, ("review", "missing_mpn")),
        (scraped(condition=None), 18000, ("review", "missing_condition")),
        (scraped(capacity_gb=None), None, ("review", "missing_capacity")),
        (
            scraped(capacity_gb=20000, title="Seagate Exos ST18000NM000J 20TB"),
            18000,
            ("review", "capacity_conflict"),
        ),
        (scraped(in_stock=False), 18000, ("ignored", "sold_out")),
        (
            scraped(capacity_gb=20000, title="Seagate Exos ST18000NM000J 20TB"),
            None,
            ("recorded", None),
        ),
        (scraped(), 18000, ("recorded", None)),
        # A drive's capacity is known, so the offer need not say it.
        (scraped(capacity_gb=None), 18000, ("recorded", None)),
        # What it is comes before whether it is sold out.
        (scraped(mpn=None, in_stock=False), None, ("review", "missing_mpn")),
        (scraped(title="HPE Q1J18A Bundle 25x1.8TB"), None, ("review", "not_a_single_drive")),
        (scraped(capacity_gb=960000), None, ("review", "implausible_capacity")),
        (
            scraped(title="HPE R0P90A 6-pack", in_stock=False),
            None,
            ("review", "not_a_single_drive"),
        ),
    ],
    ids=[
        "no MPN",
        "no condition",
        "no capacity for a new drive",
        "another capacity than the drive has",
        "sold out",
        "a new drive with its capacity",
        "a known drive at its capacity",
        "a known drive without a capacity",
        "sold out and unidentified",
        "not one drive",
        "more than a drive holds",
        "sold out and not one drive",
    ],
)
def test_the_verdict_says_what_recording_the_offer_would_do(
    offer: dict[str, Any], known: int | None, verdict: tuple[str, str | None]
) -> None:
    assert preview_verdict(offer, known) == verdict


@pytest.mark.parametrize(
    ("name", "key"),
    [("ServerPartDeals", "serverpartdeals"), ("Server Orbit", "serverorbit"), ("B&H 2", "bh2")],
)
def test_a_sources_key_is_its_names_letters_and_digits_in_lower_case(name: str, key: str) -> None:
    assert source_key(name) == key


ANSWERED = {"status": "recorded", "offer_id": "o", "price_id": "p", "review_item_id": None}


def test_a_request_sent_again_under_its_key_is_answered_as_it_was() -> None:
    assert replayed(ANSWERED, "same", "same") == ANSWERED


def test_a_key_used_for_a_different_request_is_refused() -> None:
    with pytest.raises(IdempotencyConflict, match="already used for a different request"):
        replayed(ANSWERED, "kept", "other")


@pytest.mark.parametrize("fingerprint", ["kept", "other"])
def test_a_key_kept_before_prices_were_unified_is_never_replayed(fingerprint: str) -> None:
    """Whatever the fingerprint, an answer in the old shape is not replayed as a new one."""
    legacy = {"id": "o", "mpn": "ST18000NM000J", "observations": []}
    with pytest.raises(IdempotencyConflict, match="used before prices were recorded this way"):
        replayed(legacy, "kept", fingerprint)


MATCHED = {"decision": "match", "mpn": "ST18000NM000J", "condition": "new", "capacity_gb": None}


def test_the_same_decision_sent_again_gets_the_first_answer() -> None:
    answer = {"status": "matched", "offer_id": "o"}
    assert decided_again(MATCHED, answer, dict(MATCHED)) == answer


def test_a_different_decision_on_a_decided_item_is_refused() -> None:
    with pytest.raises(DecisionConflict, match="already decided differently"):
        decided_again(MATCHED, {"status": "matched"}, {"decision": "ignore"})


IDENTITY = {"store": "serverpartdeals", "mpn": None, "condition": "new", "url": "u"}


def test_an_undecided_page_is_identified_as_the_offer_says() -> None:
    assert as_decided(IDENTITY, None) == IDENTITY


def test_a_page_decided_to_be_nothing_to_track_identifies_nothing() -> None:
    assert as_decided(IDENTITY, {"ignored": True, "mpn": None, "condition": None}) is None


def test_what_a_reviewer_decided_a_listing_is_stands_whatever_its_page_says() -> None:
    decided = {"ignored": False, "mpn": "ST18000NM000J", "condition": "used"}
    page = {**IDENTITY, "mpn": "ST1", "condition": "new"}
    assert as_decided(page, decided) == {**IDENTITY, "mpn": "ST18000NM000J", "condition": "used"}


def test_an_offer_waiting_for_review_keeps_what_a_reviewer_is_shown() -> None:
    """What the page said, as it said it: its MPN and condition as read, not as decided, and what
    it said of the drive."""
    entry = {
        "title": "Exos X18",
        "seller": "",
        "mpn": None,
        "condition": "new",
        "capacity_gb": None,
        "provenance": "collected",
        "url": "https://store.test/p/1",
        "notes": "not kept",
        "aliases": ["0XYZ18"],
        "brand": "Seagate",
        "specifications": {"interface": "sas"},
    }
    price = {"item_price_cents": 18900, "shipping_cents": None, "in_stock": True}
    decided = {**IDENTITY, "mpn": "ST18000NM000J", "condition": "used"}

    assert queued_fields(entry, decided, price, "missing_mpn") == {
        "aliases": ["0XYZ18"],
        "brand": "Seagate",
        "specifications": {"interface": "sas"},
        "title": "Exos X18",
        "seller": "",
        "capacity_gb": None,
        "provenance": "collected",
        "item_price_cents": 18900,
        "shipping_cents": None,
        "in_stock": True,
        "store": "serverpartdeals",
        "mpn": None,
        "condition": "new",
        "url": "https://store.test/p/1",
        "reason": "missing_mpn",
    }


class TestDoubt:
    """A collected offer is doubted when its title says it is not one drive, or its capacity is
    one no drive has; a person then says what it is."""

    @pytest.mark.parametrize(
        "title",
        [
            "HPE Q1J18A 45TB Bundle D3710 25x1.8TB 12GBPS SAS 10K Refurbished",
            "HPE M0S86A 30TB D3700 SC w/25x1.2TB SAS-12G 10K 2.5in Refurbished",
            "HPE R0P90A 48TB (8x6) 7.2K RPM 3.5inch LFF 6-pack OEM",
            "HPE R0Q67A 14.4TB (2.4TB x6) 10 KRPM 2.5inch New",
            "Avolusion PRO-T2 Series 28TB (14TB x2) Dual Bay JBOD USB 3.0 External Hard Drive",
            "HPE M0S88A D3700 Storage Array with 25 1TB 12G SAS 10K Refurbished",
            "Dell 46X2478 1.5TB/3TB LTO-5 SAS HH Internal Tape Refurbished",
            "HPE Q2078A LTO 8 12TB/30TB Tre-Writable Data New",
            "HPE C0H19A LTO 6 Auto Loader 20/50TB Store Ever Refurbished",
            "HPE EH900A Storageworks Lto-5 Ultrium 3280 1.50/3TB Refurbished",
            "Mellanox MCS7520 43TB/S 216 Ports QSFP28 Edr Refurbished",
        ],
    )
    def test_a_title_that_is_not_one_drive(self, title: str) -> None:
        assert doubt(title, 1000) == "not_a_single_drive"

    @pytest.mark.parametrize(
        "title",
        [
            # A count is written tight, with a small x; a model name ending in X is not one.
            "Avolusion Mini Pro-5X 3TB USB 3.0 Portable External Gaming PS5 Hard Drive",
            "Sandisk SDSP81200TAN Optimus GX PRO 850X 2TB PCIe 4.0 New",
            "Dell 2380X 1.92TB PCI-E Read Intensive Gen4 Enterprise Refurbished",
            # One drive with two actuators.
            "Seagate Exos 2X18 ST18000NM0092 18TB (2x 9TB) 7.2K RPM SATA 6Gb/s 512e Dual Actuator",
            # Two ports on one drive.
            "HPE 718291-001 1.2TB 10K RPM SAS 6GBPS HDD, 2 Ports New",
            "Seagate Exos X18 ST18000NM000J 18TB Recertified",
        ],
    )
    def test_a_title_of_one_drive(self, title: str) -> None:
        assert doubt(title, 18000) is None

    def test_a_capacity_no_drive_has(self) -> None:
        """The largest drives sold hold 245.76 TB."""
        title = "Kioxia KPM7XVUG960G 960TB SAS-24GBPS Read Intensive New"

        assert doubt(title, 960000) == "implausible_capacity"
        assert doubt(title, 256000) is None
        assert doubt(title, None) is None

    @pytest.mark.parametrize(
        ("title", "capacity_gb", "mpn", "doubted"),
        [
            # Read as 213.2 TB, a part number run into its capacity.
            ("HPE P09094-H213.2TB SAS 12GBPS Smart Carrier", 213200, "P09094-H21", True),
            ("Samsung MZ-ILT30TB 30.72TB SAS 12GBPS", 30000, "MZ-ILT30TB", True),
            ("HPE P09094-H213.2TB SAS 12GBPS Smart Carrier", 3200, "P09094-H21", False),
            # A title that names no capacity says nothing against it.
            ("HPE P09094-H21 Smart Carrier", 213200, "P09094-H21", False),
        ],
    )
    def test_a_capacity_its_own_title_reads_otherwise_is_doubted(
        self, title: str, capacity_gb: int, mpn: str, doubted: bool
    ) -> None:
        found = doubt(title, capacity_gb, mpn)
        assert found == ("implausible_capacity" if doubted else None)


def spec(**known: Any) -> dict[str, Any]:
    return {"media_type": "unknown", "form_factor": "unknown", "interface": "unknown",
            "recording_type": "unknown", "intended_use": [], **known}  # fmt: skip


def a_drive(**fields: Any) -> dict[str, Any]:
    return {"capacity_gb": 18000, "brand": None, "specifications": spec(), **fields}


class TestMergedDrive:
    """What two drives merged into one are: the target's, filled in from the source."""

    def test_the_target_keeps_what_it_has_and_takes_what_it_lacks(self) -> None:
        target = a_drive(brand="Seagate", specifications=spec(interface="sas"))
        source = a_drive(brand="SEAGATE", specifications=spec(interface="sas", media_type="hdd",
                         intended_use=["nas"]))  # fmt: skip

        assert merged_drive(target, source) == {
            "capacity_gb": 18000,
            # The target's brand stands, however the source spells another.
            "brand": "Seagate",
            "specifications": spec(interface="sas", media_type="hdd", intended_use=["nas"]),
        }

    def test_a_brand_the_target_lacks_is_the_sources(self) -> None:
        assert merged_drive(a_drive(), a_drive(brand="Toshiba"))["brand"] == "Toshiba"

    def test_intended_uses_alike_in_another_order_are_alike(self) -> None:
        target = a_drive(specifications=spec(intended_use=["nas", "enterprise"]))
        source = a_drive(specifications=spec(intended_use=["enterprise", "nas"]))

        assert merged_drive(target, source)["specifications"]["intended_use"] == [
            "nas",
            "enterprise",
        ]

    def test_what_both_know_and_differ_on_is_refused_every_field_of_it(self) -> None:
        target = a_drive(specifications=spec(interface="sas", intended_use=["nas"]))
        source = a_drive(
            capacity_gb=20000, specifications=spec(interface="sata", intended_use=["archive"])
        )

        with pytest.raises(MergeConflict) as refused:
            merged_drive(target, source)

        assert refused.value.fields == [
            "capacity_gb", "specifications.interface", "specifications.intended_use",
        ]  # fmt: skip


def test_an_offer_combined_with_another_stays_held_if_either_was_and_was_checked_when_last_checked() -> (
    None
):
    early, late = datetime(2026, 10, 3, tzinfo=UTC), datetime(2026, 10, 4, tzinfo=UTC)

    assert combined_offer(
        {"held_reason": None, "last_checked_at": late},
        {"held_reason": "not_a_single_drive", "last_checked_at": early},
    ) == {"held_reason": "not_a_single_drive", "last_checked_at": late}
    assert combined_offer(
        {"held_reason": "implausible_capacity", "last_checked_at": None},
        {"held_reason": "not_a_single_drive", "last_checked_at": early},
    ) == {"held_reason": "implausible_capacity", "last_checked_at": early}
