from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from disktracker.reporting.trends import Change, Offer, trends

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)


def offer(
    drive: str,
    *prices: tuple[float, int] | tuple[float, int, bool],
    condition: str = "new",
    store: str = "serverpartdeals",
    capacity_gb: int = 10000,
    checked: float = 0,
) -> Offer:
    """An offer whose item price changed to each amount so many days ago, oldest first; a third
    value of False records it out of stock. It was last checked `checked` days ago."""
    changes = [
        Change(NOW - timedelta(days=price[0]), price[1], price[2] if len(price) == 3 else True)
        for price in prices
    ]
    return Offer(drive, condition, store, capacity_gb, NOW - timedelta(days=checked), changes)


def market(offers: list[Offer], days: int = 30) -> dict[str, Any]:
    return trends(offers, NOW, days, quiet_days=7, by=None)["market"]


def at(series: dict[str, Any], days_ago: int) -> dict[str, Any] | None:
    return next((point for point in series["points"] if point["days_ago"] == days_ago), None)


def test_the_market_is_the_median_drive_and_the_middle_half_each_day_in_cents_per_terabyte() -> (
    None
):
    offers = [
        offer("a", (40, 10000)),
        offer("b", (40, 20000), (10, 16000)),
        offer("c", (40, 30000)),
    ]
    result = trends(offers, NOW, 30, quiet_days=7, by=None)
    assert (result["days"], result["by"], result["parts"]) == (30, None, [])
    series = result["market"]
    assert (series["counted"], series["of"]) == (3, 3)
    assert [point["days_ago"] for point in series["points"]] == list(range(30, -1, -1))
    assert at(series, 30) == {"days_ago": 30, "median": 2000, "low": 1500, "high": 2500}
    assert at(series, 11) == {"days_ago": 11, "median": 2000, "low": 1500, "high": 2500}
    # The price changed ten days ago to the moment, so that day already shows it.
    assert at(series, 10) == {"days_ago": 10, "median": 1600, "low": 1300, "high": 2300}
    assert at(series, 0) == {"days_ago": 0, "median": 1600, "low": 1300, "high": 2300}


def test_a_terabyte_is_a_thousand_gigabytes_of_the_drives_own_capacity() -> None:
    series = market(
        [offer("a", (40, 18000), capacity_gb=18000), offer("b", (40, 9600), capacity_gb=960)]
    )
    # $180 for 18 TB is $10 a terabyte; $96 for 960 GB is $100 a terabyte.
    assert at(series, 0) == {"days_ago": 0, "median": 5500, "low": 3250, "high": 7750}


def test_a_drive_counts_once_per_condition_at_the_lowest_price_any_store_asks() -> None:
    offers = [
        offer("a", (40, 20000), store="serverpartdeals"),
        offer("a", (40, 15000), (10, 25000), store="goharddrive"),
        offer("a", (40, 5000), condition="used", store="goharddrive"),
    ]
    series = market(offers)
    assert (series["counted"], series["of"]) == (2, 2)
    # New: $15 then $20 a terabyte once the cheaper store put its price up. Used: $5 throughout.
    assert at(series, 20) == {"days_ago": 20, "median": 1000, "low": 750, "high": 1250}
    assert at(series, 5) == {"days_ago": 5, "median": 1250, "low": 875, "high": 1625}


def test_only_drives_priced_as_the_period_opens_are_followed_so_an_arrival_moves_nothing() -> None:
    series = market([offer("a", (40, 20000)), offer("late", (5, 1000))])
    assert (series["counted"], series["of"]) == (1, 2)
    assert at(series, 0) == {"days_ago": 0, "median": 2000, "low": 2000, "high": 2000}


def test_a_drive_out_of_stock_is_left_out_of_the_days_it_could_not_be_bought() -> None:
    offers = [
        offer("a", (40, 10000)),
        offer("b", (40, 30000), (20, 30000, False), (10, 30000)),
        offer("gone", (40, 5000, False)),
    ]
    series = market(offers)
    # Never in stock: not followed, and not one of the drives there are prices for.
    assert (series["counted"], series["of"]) == (2, 2)
    assert at(series, 25) == {"days_ago": 25, "median": 2000, "low": 1500, "high": 2500}
    assert at(series, 15) == {"days_ago": 15, "median": 1000, "low": 1000, "high": 1000}
    assert at(series, 5) == {"days_ago": 5, "median": 2000, "low": 1500, "high": 2500}


def test_an_offer_unchecked_for_longer_than_allowed_ends_at_its_last_check() -> None:
    offers = [offer("a", (40, 10000)), offer("quiet", (40, 30000), checked=15)]
    series = market(offers)
    assert at(series, 16) == {"days_ago": 16, "median": 2000, "low": 1500, "high": 2500}
    assert at(series, 15) == {"days_ago": 15, "median": 1000, "low": 1000, "high": 1000}
    # Checked exactly as long ago as allowed still counts.
    edge = market([offer("a", (40, 10000), checked=7)])
    assert at(edge, 0) == {"days_ago": 0, "median": 1000, "low": 1000, "high": 1000}


def test_a_day_with_no_drive_to_price_has_no_point() -> None:
    series = market([offer("a", (40, 10000), (10, 10000, False))])
    assert [point["days_ago"] for point in series["points"]] == list(range(30, 10, -1))
    assert market([]) == {"counted": 0, "of": 0, "points": []}


def test_split_by_condition_each_condition_sold_has_its_own_series_in_the_usual_order() -> None:
    offers = [
        offer("a", (40, 5000), condition="used"),
        offer("a", (40, 20000), condition="new"),
        offer("b", (40, 30000), condition="new"),
    ]
    result = trends(offers, NOW, 30, quiet_days=7, by="condition")
    assert result["by"] == "condition"
    assert [part["key"] for part in result["parts"]] == ["new", "used"]
    new, used = (part["series"] for part in result["parts"])
    assert (new["counted"], new["of"]) == (2, 2)
    assert at(new, 0) == {"days_ago": 0, "median": 2500, "low": 2250, "high": 2750}
    assert at(used, 0) == {"days_ago": 0, "median": 500, "low": 500, "high": 500}
    assert at(result["market"], 0) == {"days_ago": 0, "median": 2000, "low": 1250, "high": 2500}


def test_split_by_capacity_each_size_has_its_own_series_smallest_first() -> None:
    offers = [
        offer("big", (40, 36000), capacity_gb=18000),
        offer("small", (40, 9600), capacity_gb=960),
        offer("big too", (40, 18000), capacity_gb=18000),
    ]
    parts = trends(offers, NOW, 30, quiet_days=7, by="capacity")["parts"]
    assert [part["key"] for part in parts] == ["960", "18000"]
    assert at(parts[0]["series"], 0) == {
        "days_ago": 0,
        "median": 10000,
        "low": 10000,
        "high": 10000,
    }
    assert at(parts[1]["series"], 0) == {"days_ago": 0, "median": 1500, "low": 1250, "high": 1750}


def test_split_by_store_each_store_is_set_against_the_typical_price_of_the_drives_it_shares() -> (
    None
):
    offers = [
        offer("a", (40, 10000), store="serverpartdeals"),
        offer("a", (40, 12000), (10, 10000), store="goharddrive"),
        # Nobody else sells this one, so it says nothing about how either store prices.
        offer("alone", (40, 99900), store="goharddrive"),
        offer("solo", (40, 5000), store="westerndigital"),
    ]
    parts = trends(offers, NOW, 30, quiet_days=7, by="store")["parts"]
    assert [part["key"] for part in parts] == ["goharddrive", "serverpartdeals", "westerndigital"]
    ghd, spd, wd = (part["series"] for part in parts)
    # Hundredths of a percent above the typical price ($110) of the drive both sell: $120 and $100.
    assert (ghd["counted"], ghd["of"]) == (1, 2)
    assert at(ghd, 20) == {"days_ago": 20, "median": 909, "low": 909, "high": 909}
    assert at(spd, 20) == {"days_ago": 20, "median": -909, "low": -909, "high": -909}
    # Once both ask the same, neither is above typical.
    assert at(ghd, 5) == {"days_ago": 5, "median": 0, "low": 0, "high": 0}
    assert wd == {"counted": 0, "of": 1, "points": []}


class Counted(list[Offer]):
    """Offers that count how many times the whole list is read through."""

    reads = 0

    def __iter__(self) -> Iterator[Offer]:
        self.reads += 1
        return super().__iter__()


def test_split_by_store_reads_the_offers_no_more_often_however_many_drives_are_sold() -> None:
    def shared(drives: int) -> Counted:
        return Counted(
            offer(f"drive-{number}", (40, 10000), store=store)
            for number in range(drives)
            for store in ("serverpartdeals", "goharddrive")
        )

    few, many = shared(2), shared(40)
    trends(few, NOW, 30, quiet_days=7, by="store")
    trends(many, NOW, 30, quiet_days=7, by="store")
    assert many.reads == few.reads


@pytest.mark.parametrize("days", [30, 90, 180])
def test_the_period_is_as_many_days_as_asked_for(days: int) -> None:
    series = market([offer("a", (400, 10000))], days)
    assert [point["days_ago"] for point in series["points"]] == list(range(days, -1, -1))


def test_a_trend_says_when_the_first_price_it_could_follow_was_seen() -> None:
    """However long the period: so a period too long for any drive can say when it will fill."""
    offers = [offer("a", (12, 10000), (3, 9000)), offer("b", (5, 20000))]

    assert (
        trends(offers, NOW, 7, quiet_days=7, by=None)["since"]
        == (NOW - timedelta(days=12)).isoformat()
    )
    assert trends([], NOW, 7, quiet_days=7, by=None)["since"] is None
