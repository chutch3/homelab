from typing import Literal

PricesTodayRecordingTypeType0 = Literal['cmr', 'smr', 'unknown']

PRICES_TODAY_RECORDING_TYPE_TYPE_0_VALUES: set[PricesTodayRecordingTypeType0] = { 'cmr', 'smr', 'unknown',  }

def check_prices_today_recording_type_type_0(value: str) -> PricesTodayRecordingTypeType0:
    if value in PRICES_TODAY_RECORDING_TYPE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICES_TODAY_RECORDING_TYPE_TYPE_0_VALUES!r}")
