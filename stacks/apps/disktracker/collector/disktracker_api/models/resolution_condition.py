from typing import Literal

ResolutionCondition = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

RESOLUTION_CONDITION_VALUES: set[ResolutionCondition] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_resolution_condition(value: str) -> ResolutionCondition:
    if value in RESOLUTION_CONDITION_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {RESOLUTION_CONDITION_VALUES!r}")
