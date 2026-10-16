from typing import Literal

PriceTrendsByType0 = Literal['capacity', 'condition', 'store']

PRICE_TRENDS_BY_TYPE_0_VALUES: set[PriceTrendsByType0] = { 'capacity', 'condition', 'store',  }

def check_price_trends_by_type_0(value: str) -> PriceTrendsByType0:
    if value in PRICE_TRENDS_BY_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_TRENDS_BY_TYPE_0_VALUES!r}")
