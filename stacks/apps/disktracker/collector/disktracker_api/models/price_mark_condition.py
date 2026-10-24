from typing import Literal

PriceMarkCondition = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

PRICE_MARK_CONDITION_VALUES: set[PriceMarkCondition] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_price_mark_condition(value: str) -> PriceMarkCondition:
    if value in PRICE_MARK_CONDITION_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_MARK_CONDITION_VALUES!r}")
