from typing import Literal

MarketIntendedUseType0 = Literal['archive', 'desktop', 'enterprise', 'nas', 'surveillance']

MARKET_INTENDED_USE_TYPE_0_VALUES: set[MarketIntendedUseType0] = { 'archive', 'desktop', 'enterprise', 'nas', 'surveillance',  }

def check_market_intended_use_type_0(value: str) -> MarketIntendedUseType0:
    if value in MARKET_INTENDED_USE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MARKET_INTENDED_USE_TYPE_0_VALUES!r}")
