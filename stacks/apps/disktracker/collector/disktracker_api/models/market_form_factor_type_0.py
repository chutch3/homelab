from typing import Literal

MarketFormFactorType0 = Literal['2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown']

MARKET_FORM_FACTOR_TYPE_0_VALUES: set[MarketFormFactorType0] = { '2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown',  }

def check_market_form_factor_type_0(value: str) -> MarketFormFactorType0:
    if value in MARKET_FORM_FACTOR_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MARKET_FORM_FACTOR_TYPE_0_VALUES!r}")
