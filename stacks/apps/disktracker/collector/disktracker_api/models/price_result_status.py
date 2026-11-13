from typing import Literal

PriceResultStatus = Literal['ignored', 'queued', 'recorded']

PRICE_RESULT_STATUS_VALUES: set[PriceResultStatus] = { 'ignored', 'queued', 'recorded',  }

def check_price_result_status(value: str) -> PriceResultStatus:
    if value in PRICE_RESULT_STATUS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_RESULT_STATUS_VALUES!r}")
