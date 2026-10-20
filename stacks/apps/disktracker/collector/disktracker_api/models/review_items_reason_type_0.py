from typing import Literal

ReviewItemsReasonType0 = Literal['alias_conflict', 'capacity_conflict', 'implausible_capacity', 'missing_capacity', 'missing_condition', 'missing_mpn', 'missing_price', 'not_a_single_drive']

REVIEW_ITEMS_REASON_TYPE_0_VALUES: set[ReviewItemsReasonType0] = { 'alias_conflict', 'capacity_conflict', 'implausible_capacity', 'missing_capacity', 'missing_condition', 'missing_mpn', 'missing_price', 'not_a_single_drive',  }

def check_review_items_reason_type_0(value: str) -> ReviewItemsReasonType0:
    if value in REVIEW_ITEMS_REASON_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {REVIEW_ITEMS_REASON_TYPE_0_VALUES!r}")
