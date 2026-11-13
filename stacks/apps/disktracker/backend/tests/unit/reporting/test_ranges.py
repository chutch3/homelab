"""A drive's price range over a period, as the frontend worked it out before the server did: the
same cases, the same answers."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from disktracker.reporting.ranges import lowest_steps, price_range

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)


def ago(days: float) -> datetime:
    return NOW - timedelta(days=days)


def price(name: str, days: float, item: int, in_stock: bool = True) -> dict[str, Any]:
    return {"id": name, "observed_at": ago(days), "entered_at": ago(days),
            "item_price_cents": item, "in_stock": in_stock}  # fmt: skip


def offer(prices: list[dict[str, Any]], last_checked_days_ago: float = 0) -> Any:
    return prices, ago(last_checked_days_ago)


def test_it_follows_the_lowest_item_price_at_any_store_weighing_each_by_the_days_it_held() -> None:
    spd = offer([price("spd-1", 60, 20000), price("spd-2", 20, 18000)])
    ghd = offer([price("ghd-1", 100, 19000), price("ghd-2", 40, 17000), price("ghd-3", 10, 18500)])
    # $190 for 50 days, $170 for 30, $180 for 10.
    assert price_range([spd, ghd], NOW, 90, 7) == {
        "today": 18000, "low": 17000, "high": 19000, "average": 18222, "days": 90
    }  # fmt: skip


def test_it_counts_only_the_days_there_are_prices_for_when_the_offer_is_newer() -> None:
    recent = offer([price("a-1", 12, 15000), price("a-2", 3, 14000)])
    assert price_range([recent], NOW, 90, 7) == {
        "today": 14000, "low": 14000, "high": 15000, "average": 14750, "days": 12
    }  # fmt: skip


def test_it_takes_the_price_in_force_as_the_period_opens_and_nothing_older() -> None:
    old = offer([price("a-1", 200, 9000), price("a-2", 120, 20000), price("a-3", 30, 21000)])
    assert price_range([old], NOW, 90, 7) == {
        "today": 21000, "low": 20000, "high": 21000, "average": 20333, "days": 90
    }  # fmt: skip


def test_it_does_not_count_a_price_while_the_offer_was_out_of_stock() -> None:
    gone = offer(
        [price("a-1", 40, 20000), price("a-2", 30, 10000, in_stock=False), price("a-3", 10, 19000)]
    )
    assert price_range([gone], NOW, 90, 7) == {
        "today": 19000, "low": 19000, "high": 20000, "average": 19500, "days": 40
    }  # fmt: skip


def test_it_has_no_price_today_when_every_offer_is_out_of_stock() -> None:
    sold_out = offer([price("a-1", 20, 20000), price("a-2", 5, 20000, in_stock=False)])
    assert price_range([sold_out], NOW, 90, 7) == {
        "today": None, "low": 20000, "high": 20000, "average": 20000, "days": 20
    }  # fmt: skip


def test_it_ends_an_offers_price_at_its_last_check_once_unchecked_too_long() -> None:
    quiet = offer([price("q-1", 60, 15000)], 30)
    live = offer([price("l-1", 60, 20000)])
    assert price_range([quiet, live], NOW, 90, 7) == {
        "today": 20000, "low": 15000, "high": 20000, "average": 17500, "days": 60
    }  # fmt: skip


def test_it_still_counts_an_offer_last_checked_exactly_as_long_ago_as_allowed() -> None:
    edge = offer([price("e-1", 20, 15000)], 7)
    assert price_range([edge], NOW, 90, 7) == {
        "today": 15000, "low": 15000, "high": 15000, "average": 15000, "days": 20
    }  # fmt: skip


def test_it_is_that_one_price_when_the_first_was_recorded_this_instant() -> None:
    assert price_range([offer([price("a-1", 0, 15000)])], NOW, 90, 7) == {
        "today": 15000, "low": 15000, "high": 15000, "average": 15000, "days": 0
    }  # fmt: skip


def test_a_price_recorded_this_instant_is_todays_and_moves_the_low_not_the_average() -> None:
    cut = offer([price("a-1", 10, 20000), price("a-2", 0, 18000)])
    assert price_range([cut], NOW, 90, 7) == {
        "today": 18000, "low": 18000, "high": 20000, "average": 20000, "days": 10
    }  # fmt: skip


def test_it_is_absent_when_nothing_was_in_stock_during_the_period() -> None:
    assert price_range([], NOW, 90, 7) is None
    assert price_range([offer([price("a-1", 20, 20000, in_stock=False)])], NOW, 90, 7) is None
    assert price_range([offer([price("o-1", 200, 20000)], 150)], NOW, 90, 7) is None
    # Seen once, 30 days ago, and never checked again: it held for no time at all.
    assert price_range([offer([price("s-1", 30, 20000)], 30)], NOW, 90, 7) is None


EXAMPLES = json.loads((Path(__file__).parents[4] / "tests/examples/lowest-prices.json").read_text())


@pytest.mark.parametrize("case", EXAMPLES["cases"], ids=lambda case: case["name"])
def test_the_lowest_price_steps_are_those_the_drive_chart_draws(case: dict[str, Any]) -> None:
    offers = [
        offer(
            [
                price(
                    f"{index}-{number}",
                    entry["days_ago"],
                    entry["item"],
                    entry.get("in_stock", True),
                )
                for number, entry in enumerate(seen["prices"])
            ],
            seen["checked_days_ago"],
        )
        for index, seen in enumerate(case["offers"])
    ]
    steps, today = lowest_steps(offers, NOW, EXAMPLES["days"], EXAMPLES["quiet_days"])

    def days_ago(moment: float) -> float:
        return round((NOW.timestamp() - moment) / 86400, 6)

    assert [[days_ago(step.start), days_ago(step.end), step.price] for step in steps] == case[
        "lowest"
    ]
    assert sorted(today) == case["today"]
