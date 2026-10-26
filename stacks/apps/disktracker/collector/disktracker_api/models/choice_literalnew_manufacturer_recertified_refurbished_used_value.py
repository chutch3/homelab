from typing import Literal

ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsedValue = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

CHOICE_LITERALNEW_MANUFACTURER_RECERTIFIED_REFURBISHED_USED_VALUE_VALUES: set[ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsedValue] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_choice_literalnew_manufacturer_recertified_refurbished_used_value(value: str) -> ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsedValue:
    if value in CHOICE_LITERALNEW_MANUFACTURER_RECERTIFIED_REFURBISHED_USED_VALUE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CHOICE_LITERALNEW_MANUFACTURER_RECERTIFIED_REFURBISHED_USED_VALUE_VALUES!r}")
