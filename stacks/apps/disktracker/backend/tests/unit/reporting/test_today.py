"""What drives cost today, by the terabyte: one mark for each drive in each condition it is in
stock in, placed at the lowest item price asked for it."""

from datetime import UTC, datetime, timedelta
from typing import Any

from disktracker.reporting.today import marks

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)


def today_offer(name: str, drive: str, cents: int, **fields: Any) -> dict[str, Any]:
    return {"id": name, "drive_id": drive, "condition": "new", "title": name,
            "capacity_gb": 18000, "item_price_cents": cents, "in_stock": True,
            "last_checked_at": NOW, **fields}  # fmt: skip


def test_today_has_one_mark_for_each_condition_a_drive_is_in_stock_in_cheapest_first() -> None:
    found = marks(
        [
            today_offer(
                "spd", "exos", 19800, condition="manufacturer_recertified", title="Exos X18"
            ),
            today_offer(
                "ghd", "exos", 18000, condition="manufacturer_recertified", title="Exos X18"
            ),
            today_offer("new", "exos", 28800, title="Exos X18"),
            today_offer("Small drive", "small", 9600, capacity_gb=960),
        ],
        NOW,
        7,
    )
    assert found == [
        {"drive_id": "exos", "condition": "manufacturer_recertified", "title": "Exos X18",
         "capacity_gb": 18000, "per_tb_cents": 1000, "lowest": True},
        {"drive_id": "exos", "condition": "new", "title": "Exos X18",
         "capacity_gb": 18000, "per_tb_cents": 1600, "lowest": False},
        {"drive_id": "small", "condition": "new", "title": "Small drive",
         "capacity_gb": 960, "per_tb_cents": 10000, "lowest": False},
    ]  # fmt: skip


def test_today_leaves_out_what_is_sold_out_and_never_calls_an_unchecked_offer_lowest() -> None:
    found = marks(
        [
            today_offer("Sold out", "a", 1000, in_stock=False),
            today_offer("Unchecked", "b", 9000, last_checked_at=NOW - timedelta(days=8)),
            today_offer("Fresh", "c", 18000),
        ],
        NOW,
        7,
    )
    assert [(mark["title"], mark["per_tb_cents"], mark["lowest"]) for mark in found] == [
        ("Unchecked", 500, False),
        ("Fresh", 1000, True),
    ]
    assert marks([], NOW, 7) == []
