from typing import Literal

ReviewItemProvenance = Literal['collected', 'manual']

REVIEW_ITEM_PROVENANCE_VALUES: set[ReviewItemProvenance] = { 'collected', 'manual',  }

def check_review_item_provenance(value: str) -> ReviewItemProvenance:
    if value in REVIEW_ITEM_PROVENANCE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {REVIEW_ITEM_PROVENANCE_VALUES!r}")
