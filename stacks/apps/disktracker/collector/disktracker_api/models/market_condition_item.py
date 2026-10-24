from typing import Literal

MarketConditionItem = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

MARKET_CONDITION_ITEM_VALUES: set[MarketConditionItem] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_market_condition_item(value: str) -> MarketConditionItem:
    if value in MARKET_CONDITION_ITEM_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MARKET_CONDITION_ITEM_VALUES!r}")
