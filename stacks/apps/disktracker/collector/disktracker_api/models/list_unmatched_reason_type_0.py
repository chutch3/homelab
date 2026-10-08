from typing import Literal

ListUnmatchedReasonType0 = Literal['capacity_conflict', 'missing_capacity', 'missing_condition', 'missing_mpn', 'missing_price']

LIST_UNMATCHED_REASON_TYPE_0_VALUES: set[ListUnmatchedReasonType0] = { 'capacity_conflict', 'missing_capacity', 'missing_condition', 'missing_mpn', 'missing_price',  }

def check_list_unmatched_reason_type_0(value: str) -> ListUnmatchedReasonType0:
    if value in LIST_UNMATCHED_REASON_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_UNMATCHED_REASON_TYPE_0_VALUES!r}")
