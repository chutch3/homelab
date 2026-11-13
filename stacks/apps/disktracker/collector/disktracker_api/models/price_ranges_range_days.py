from typing import Literal

PriceRangesRangeDays = Literal[30, 90, 180]

PRICE_RANGES_RANGE_DAYS_VALUES: set[PriceRangesRangeDays] = { 30, 90, 180,  }

def check_price_ranges_range_days(value: int) -> PriceRangesRangeDays:
    if value in PRICE_RANGES_RANGE_DAYS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_RANGES_RANGE_DAYS_VALUES!r}")
