from typing import Literal

SpecificationsInputIntendedUseItem = Literal['archive', 'desktop', 'enterprise', 'nas', 'surveillance']

SPECIFICATIONS_INPUT_INTENDED_USE_ITEM_VALUES: set[SpecificationsInputIntendedUseItem] = { 'archive', 'desktop', 'enterprise', 'nas', 'surveillance',  }

def check_specifications_input_intended_use_item(value: str) -> SpecificationsInputIntendedUseItem:
    if value in SPECIFICATIONS_INPUT_INTENDED_USE_ITEM_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_INPUT_INTENDED_USE_ITEM_VALUES!r}")
