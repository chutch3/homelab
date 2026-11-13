from typing import Literal

MarketMediaTypeType0 = Literal['flash_card', 'hdd', 'ssd', 'unknown']

MARKET_MEDIA_TYPE_TYPE_0_VALUES: set[MarketMediaTypeType0] = { 'flash_card', 'hdd', 'ssd', 'unknown',  }

def check_market_media_type_type_0(value: str) -> MarketMediaTypeType0:
    if value in MARKET_MEDIA_TYPE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MARKET_MEDIA_TYPE_TYPE_0_VALUES!r}")
