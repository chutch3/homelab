from typing import Literal

OfferCondition = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

OFFER_CONDITION_VALUES: set[OfferCondition] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_offer_condition(value: str) -> OfferCondition:
    if value in OFFER_CONDITION_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {OFFER_CONDITION_VALUES!r}")
