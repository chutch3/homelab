from typing import Literal

ConditionPricesCondition = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

CONDITION_PRICES_CONDITION_VALUES: set[ConditionPricesCondition] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_condition_prices_condition(value: str) -> ConditionPricesCondition:
    if value in CONDITION_PRICES_CONDITION_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CONDITION_PRICES_CONDITION_VALUES!r}")
