from typing import Literal

PriceTrendsRecordingTypeType0 = Literal['cmr', 'smr', 'unknown']

PRICE_TRENDS_RECORDING_TYPE_TYPE_0_VALUES: set[PriceTrendsRecordingTypeType0] = { 'cmr', 'smr', 'unknown',  }

def check_price_trends_recording_type_type_0(value: str) -> PriceTrendsRecordingTypeType0:
    if value in PRICE_TRENDS_RECORDING_TYPE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_TRENDS_RECORDING_TYPE_TYPE_0_VALUES!r}")
