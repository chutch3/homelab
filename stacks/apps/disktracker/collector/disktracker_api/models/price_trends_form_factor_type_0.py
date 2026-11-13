from typing import Literal

PriceTrendsFormFactorType0 = Literal['2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown']

PRICE_TRENDS_FORM_FACTOR_TYPE_0_VALUES: set[PriceTrendsFormFactorType0] = { '2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown',  }

def check_price_trends_form_factor_type_0(value: str) -> PriceTrendsFormFactorType0:
    if value in PRICE_TRENDS_FORM_FACTOR_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_TRENDS_FORM_FACTOR_TYPE_0_VALUES!r}")
