from typing import Literal

UnmatchedConditionType0 = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

UNMATCHED_CONDITION_TYPE_0_VALUES: set[UnmatchedConditionType0] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_unmatched_condition_type_0(value: str) -> UnmatchedConditionType0:
    if value in UNMATCHED_CONDITION_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UNMATCHED_CONDITION_TYPE_0_VALUES!r}")
