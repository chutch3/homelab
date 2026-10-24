from typing import Literal

MarketRecordingTypeType0 = Literal['cmr', 'smr', 'unknown']

MARKET_RECORDING_TYPE_TYPE_0_VALUES: set[MarketRecordingTypeType0] = { 'cmr', 'smr', 'unknown',  }

def check_market_recording_type_type_0(value: str) -> MarketRecordingTypeType0:
    if value in MARKET_RECORDING_TYPE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MARKET_RECORDING_TYPE_TYPE_0_VALUES!r}")
