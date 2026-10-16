from typing import Literal

OfferDoubtType0 = Literal['implausible_capacity', 'not_a_single_drive']

OFFER_DOUBT_TYPE_0_VALUES: set[OfferDoubtType0] = { 'implausible_capacity', 'not_a_single_drive',  }

def check_offer_doubt_type_0(value: str) -> OfferDoubtType0:
    if value in OFFER_DOUBT_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {OFFER_DOUBT_TYPE_0_VALUES!r}")
