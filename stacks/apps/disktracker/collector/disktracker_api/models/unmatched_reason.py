from typing import Literal

UnmatchedReason = Literal['capacity_conflict', 'missing_capacity', 'missing_condition', 'missing_mpn', 'missing_price']

UNMATCHED_REASON_VALUES: set[UnmatchedReason] = { 'capacity_conflict', 'missing_capacity', 'missing_condition', 'missing_mpn', 'missing_price',  }

def check_unmatched_reason(value: str) -> UnmatchedReason:
    if value in UNMATCHED_REASON_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {UNMATCHED_REASON_VALUES!r}")
