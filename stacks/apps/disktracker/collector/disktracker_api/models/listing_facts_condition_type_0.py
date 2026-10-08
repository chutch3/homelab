from typing import Literal

ListingFactsConditionType0 = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

LISTING_FACTS_CONDITION_TYPE_0_VALUES: set[ListingFactsConditionType0] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_listing_facts_condition_type_0(value: str) -> ListingFactsConditionType0:
    if value in LISTING_FACTS_CONDITION_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LISTING_FACTS_CONDITION_TYPE_0_VALUES!r}")
