from typing import Literal

PriceTrendsMediaTypeType0 = Literal['flash_card', 'hdd', 'ssd', 'unknown']

PRICE_TRENDS_MEDIA_TYPE_TYPE_0_VALUES: set[PriceTrendsMediaTypeType0] = { 'flash_card', 'hdd', 'ssd', 'unknown',  }

def check_price_trends_media_type_type_0(value: str) -> PriceTrendsMediaTypeType0:
    if value in PRICE_TRENDS_MEDIA_TYPE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_TRENDS_MEDIA_TYPE_TYPE_0_VALUES!r}")
