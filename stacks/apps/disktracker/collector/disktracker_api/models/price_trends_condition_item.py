from typing import Literal

PriceTrendsConditionItem = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

PRICE_TRENDS_CONDITION_ITEM_VALUES: set[PriceTrendsConditionItem] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_price_trends_condition_item(value: str) -> PriceTrendsConditionItem:
    if value in PRICE_TRENDS_CONDITION_ITEM_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_TRENDS_CONDITION_ITEM_VALUES!r}")
