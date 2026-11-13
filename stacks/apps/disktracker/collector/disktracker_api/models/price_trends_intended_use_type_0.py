from typing import Literal

PriceTrendsIntendedUseType0 = Literal['archive', 'desktop', 'enterprise', 'nas', 'surveillance']

PRICE_TRENDS_INTENDED_USE_TYPE_0_VALUES: set[PriceTrendsIntendedUseType0] = { 'archive', 'desktop', 'enterprise', 'nas', 'surveillance',  }

def check_price_trends_intended_use_type_0(value: str) -> PriceTrendsIntendedUseType0:
    if value in PRICE_TRENDS_INTENDED_USE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_TRENDS_INTENDED_USE_TYPE_0_VALUES!r}")
