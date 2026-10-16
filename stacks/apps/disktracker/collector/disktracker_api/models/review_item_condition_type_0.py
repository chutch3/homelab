from typing import Literal

ReviewItemConditionType0 = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

REVIEW_ITEM_CONDITION_TYPE_0_VALUES: set[ReviewItemConditionType0] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_review_item_condition_type_0(value: str) -> ReviewItemConditionType0:
    if value in REVIEW_ITEM_CONDITION_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {REVIEW_ITEM_CONDITION_TYPE_0_VALUES!r}")
