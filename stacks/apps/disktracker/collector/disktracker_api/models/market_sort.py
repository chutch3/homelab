from typing import Literal

MarketSort = Literal['capacity-asc', 'capacity-desc', 'checked-asc', 'checked-desc', 'total-asc', 'total-desc', 'unit-asc', 'unit-desc']

MARKET_SORT_VALUES: set[MarketSort] = { 'capacity-asc', 'capacity-desc', 'checked-asc', 'checked-desc', 'total-asc', 'total-desc', 'unit-asc', 'unit-desc',  }

def check_market_sort(value: str) -> MarketSort:
    if value in MARKET_SORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MARKET_SORT_VALUES!r}")
