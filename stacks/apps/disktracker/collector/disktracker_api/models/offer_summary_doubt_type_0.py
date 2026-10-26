from typing import Literal

OfferSummaryDoubtType0 = Literal['implausible_capacity', 'not_a_single_drive']

OFFER_SUMMARY_DOUBT_TYPE_0_VALUES: set[OfferSummaryDoubtType0] = { 'implausible_capacity', 'not_a_single_drive',  }

def check_offer_summary_doubt_type_0(value: str) -> OfferSummaryDoubtType0:
    if value in OFFER_SUMMARY_DOUBT_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {OFFER_SUMMARY_DOUBT_TYPE_0_VALUES!r}")
