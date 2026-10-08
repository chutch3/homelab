from datetime import UTC, datetime
from typing import Any

import pytest

from disktracker.rules import (
    CapacityConflict,
    CapacityRequired,
    PriceRequired,
    fill_unknown,
    merge_plan,
    missing_detail,
    new_aliases,
    queue_reason,
    unchanged,
    with_carried_price,
)

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
