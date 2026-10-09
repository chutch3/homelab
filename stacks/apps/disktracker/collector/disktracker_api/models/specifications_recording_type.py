from typing import Literal

SpecificationsRecordingType = Literal['cmr', 'smr', 'unknown']

SPECIFICATIONS_RECORDING_TYPE_VALUES: set[SpecificationsRecordingType] = { 'cmr', 'smr', 'unknown',  }

def check_specifications_recording_type(value: str) -> SpecificationsRecordingType:
    if value in SPECIFICATIONS_RECORDING_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_RECORDING_TYPE_VALUES!r}")
