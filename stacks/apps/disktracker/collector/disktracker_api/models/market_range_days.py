from typing import Literal

MarketRangeDays = Literal[30, 90, 180]

MARKET_RANGE_DAYS_VALUES: set[MarketRangeDays] = { 30, 90, 180,  }

def check_market_range_days(value: int) -> MarketRangeDays:
    if value in MARKET_RANGE_DAYS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MARKET_RANGE_DAYS_VALUES!r}")
