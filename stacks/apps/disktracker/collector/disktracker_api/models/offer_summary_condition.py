from typing import Literal

OfferSummaryCondition = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

OFFER_SUMMARY_CONDITION_VALUES: set[OfferSummaryCondition] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_offer_summary_condition(value: str) -> OfferSummaryCondition:
    if value in OFFER_SUMMARY_CONDITION_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {OFFER_SUMMARY_CONDITION_VALUES!r}")
