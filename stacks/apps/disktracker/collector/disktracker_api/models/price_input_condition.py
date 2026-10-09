from typing import Literal

PriceInputCondition = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

PRICE_INPUT_CONDITION_VALUES: set[PriceInputCondition] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_price_input_condition(value: str) -> PriceInputCondition:
    if value in PRICE_INPUT_CONDITION_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_INPUT_CONDITION_VALUES!r}")
