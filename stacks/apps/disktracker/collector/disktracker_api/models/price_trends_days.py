from typing import Literal

PriceTrendsDays = Literal[7, 14, 30, 90, 180]

PRICE_TRENDS_DAYS_VALUES: set[PriceTrendsDays] = { 7, 14, 30, 90, 180,  }

def check_price_trends_days(value: int) -> PriceTrendsDays:
    if value in PRICE_TRENDS_DAYS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_TRENDS_DAYS_VALUES!r}")
