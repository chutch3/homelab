from typing import Literal

SpecificationsIntendedUseItem = Literal['archive', 'desktop', 'enterprise', 'nas', 'surveillance']

SPECIFICATIONS_INTENDED_USE_ITEM_VALUES: set[SpecificationsIntendedUseItem] = { 'archive', 'desktop', 'enterprise', 'nas', 'surveillance',  }

def check_specifications_intended_use_item(value: str) -> SpecificationsIntendedUseItem:
    if value in SPECIFICATIONS_INTENDED_USE_ITEM_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_INTENDED_USE_ITEM_VALUES!r}")
