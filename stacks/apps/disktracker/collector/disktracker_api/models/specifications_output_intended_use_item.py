from typing import Literal

SpecificationsOutputIntendedUseItem = Literal['archive', 'desktop', 'enterprise', 'nas', 'surveillance']

SPECIFICATIONS_OUTPUT_INTENDED_USE_ITEM_VALUES: set[SpecificationsOutputIntendedUseItem] = { 'archive', 'desktop', 'enterprise', 'nas', 'surveillance',  }

def check_specifications_output_intended_use_item(value: str) -> SpecificationsOutputIntendedUseItem:
    if value in SPECIFICATIONS_OUTPUT_INTENDED_USE_ITEM_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_OUTPUT_INTENDED_USE_ITEM_VALUES!r}")
