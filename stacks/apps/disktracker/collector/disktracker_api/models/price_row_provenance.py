from typing import Literal

PriceRowProvenance = Literal['collected', 'manual']

PRICE_ROW_PROVENANCE_VALUES: set[PriceRowProvenance] = { 'collected', 'manual',  }

def check_price_row_provenance(value: str) -> PriceRowProvenance:
    if value in PRICE_ROW_PROVENANCE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_ROW_PROVENANCE_VALUES!r}")
