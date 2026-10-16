from typing import Literal

PricesTodayIntendedUseType0 = Literal['archive', 'desktop', 'enterprise', 'nas', 'surveillance']

PRICES_TODAY_INTENDED_USE_TYPE_0_VALUES: set[PricesTodayIntendedUseType0] = { 'archive', 'desktop', 'enterprise', 'nas', 'surveillance',  }

def check_prices_today_intended_use_type_0(value: str) -> PricesTodayIntendedUseType0:
    if value in PRICES_TODAY_INTENDED_USE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICES_TODAY_INTENDED_USE_TYPE_0_VALUES!r}")
