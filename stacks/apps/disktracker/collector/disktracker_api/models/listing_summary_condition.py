from typing import Literal

ListingSummaryCondition = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

LISTING_SUMMARY_CONDITION_VALUES: set[ListingSummaryCondition] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_listing_summary_condition(value: str) -> ListingSummaryCondition:
    if value in LISTING_SUMMARY_CONDITION_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LISTING_SUMMARY_CONDITION_VALUES!r}")
