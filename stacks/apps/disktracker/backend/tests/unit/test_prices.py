import pytest

from disktracker.prices import comparable_price


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
