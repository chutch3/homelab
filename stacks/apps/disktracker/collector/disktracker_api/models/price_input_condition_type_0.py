from typing import Literal

PriceInputConditionType0 = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

PRICE_INPUT_CONDITION_TYPE_0_VALUES: set[PriceInputConditionType0] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_price_input_condition_type_0(value: str) -> PriceInputConditionType0:
    if value in PRICE_INPUT_CONDITION_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_INPUT_CONDITION_TYPE_0_VALUES!r}")
