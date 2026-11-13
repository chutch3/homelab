from typing import Literal

PriceInputProvenance = Literal['collected', 'manual']

PRICE_INPUT_PROVENANCE_VALUES: set[PriceInputProvenance] = { 'collected', 'manual',  }

def check_price_input_provenance(value: str) -> PriceInputProvenance:
    if value in PRICE_INPUT_PROVENANCE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_INPUT_PROVENANCE_VALUES!r}")
