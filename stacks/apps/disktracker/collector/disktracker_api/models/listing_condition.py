from typing import Literal

ListingCondition = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

LISTING_CONDITION_VALUES: set[ListingCondition] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_listing_condition(value: str) -> ListingCondition:
    if value in LISTING_CONDITION_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LISTING_CONDITION_VALUES!r}")
