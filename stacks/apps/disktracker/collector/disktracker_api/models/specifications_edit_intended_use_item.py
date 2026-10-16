from typing import Literal

SpecificationsEditIntendedUseItem = Literal['archive', 'desktop', 'enterprise', 'nas', 'surveillance']

SPECIFICATIONS_EDIT_INTENDED_USE_ITEM_VALUES: set[SpecificationsEditIntendedUseItem] = { 'archive', 'desktop', 'enterprise', 'nas', 'surveillance',  }

def check_specifications_edit_intended_use_item(value: str) -> SpecificationsEditIntendedUseItem:
    if value in SPECIFICATIONS_EDIT_INTENDED_USE_ITEM_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_EDIT_INTENDED_USE_ITEM_VALUES!r}")
