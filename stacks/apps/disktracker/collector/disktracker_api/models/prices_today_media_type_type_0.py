from typing import Literal

PricesTodayMediaTypeType0 = Literal['flash_card', 'hdd', 'ssd', 'unknown']

PRICES_TODAY_MEDIA_TYPE_TYPE_0_VALUES: set[PricesTodayMediaTypeType0] = { 'flash_card', 'hdd', 'ssd', 'unknown',  }

def check_prices_today_media_type_type_0(value: str) -> PricesTodayMediaTypeType0:
    if value in PRICES_TODAY_MEDIA_TYPE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICES_TODAY_MEDIA_TYPE_TYPE_0_VALUES!r}")
