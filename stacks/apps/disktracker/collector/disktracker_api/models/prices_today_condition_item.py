from typing import Literal

PricesTodayConditionItem = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

PRICES_TODAY_CONDITION_ITEM_VALUES: set[PricesTodayConditionItem] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_prices_today_condition_item(value: str) -> PricesTodayConditionItem:
    if value in PRICES_TODAY_CONDITION_ITEM_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICES_TODAY_CONDITION_ITEM_VALUES!r}")
