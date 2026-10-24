from typing import Literal

PricesTodayFormFactorType0 = Literal['2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown']

PRICES_TODAY_FORM_FACTOR_TYPE_0_VALUES: set[PricesTodayFormFactorType0] = { '2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown',  }

def check_prices_today_form_factor_type_0(value: str) -> PricesTodayFormFactorType0:
    if value in PRICES_TODAY_FORM_FACTOR_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICES_TODAY_FORM_FACTOR_TYPE_0_VALUES!r}")
