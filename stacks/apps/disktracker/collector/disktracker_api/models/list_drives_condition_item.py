from typing import Literal

ListDrivesConditionItem = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

LIST_DRIVES_CONDITION_ITEM_VALUES: set[ListDrivesConditionItem] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_list_drives_condition_item(value: str) -> ListDrivesConditionItem:
    if value in LIST_DRIVES_CONDITION_ITEM_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_DRIVES_CONDITION_ITEM_VALUES!r}")
