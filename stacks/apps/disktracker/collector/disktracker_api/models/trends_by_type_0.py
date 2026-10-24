from typing import Literal

TrendsByType0 = Literal['capacity', 'condition', 'store']

TRENDS_BY_TYPE_0_VALUES: set[TrendsByType0] = { 'capacity', 'condition', 'store',  }

def check_trends_by_type_0(value: str) -> TrendsByType0:
    if value in TRENDS_BY_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {TRENDS_BY_TYPE_0_VALUES!r}")
