from typing import Literal

PriceInputOnUnmatched = Literal['queue', 'reject']

PRICE_INPUT_ON_UNMATCHED_VALUES: set[PriceInputOnUnmatched] = { 'queue', 'reject',  }

def check_price_input_on_unmatched(value: str) -> PriceInputOnUnmatched:
    if value in PRICE_INPUT_ON_UNMATCHED_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_INPUT_ON_UNMATCHED_VALUES!r}")
