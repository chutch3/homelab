from typing import Literal

ReviewItemReason = Literal['capacity_conflict', 'implausible_capacity', 'missing_capacity', 'missing_condition', 'missing_mpn', 'missing_price', 'not_a_single_drive']

REVIEW_ITEM_REASON_VALUES: set[ReviewItemReason] = { 'capacity_conflict', 'implausible_capacity', 'missing_capacity', 'missing_condition', 'missing_mpn', 'missing_price', 'not_a_single_drive',  }

def check_review_item_reason(value: str) -> ReviewItemReason:
    if value in REVIEW_ITEM_REASON_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {REVIEW_ITEM_REASON_VALUES!r}")
