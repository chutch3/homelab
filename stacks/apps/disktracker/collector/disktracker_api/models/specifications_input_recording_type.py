from typing import Literal

SpecificationsInputRecordingType = Literal['cmr', 'smr', 'unknown']

SPECIFICATIONS_INPUT_RECORDING_TYPE_VALUES: set[SpecificationsInputRecordingType] = { 'cmr', 'smr', 'unknown',  }

def check_specifications_input_recording_type(value: str) -> SpecificationsInputRecordingType:
    if value in SPECIFICATIONS_INPUT_RECORDING_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_INPUT_RECORDING_TYPE_VALUES!r}")
