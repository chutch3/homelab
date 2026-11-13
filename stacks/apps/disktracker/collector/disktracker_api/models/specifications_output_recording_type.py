from typing import Literal

SpecificationsOutputRecordingType = Literal['cmr', 'smr', 'unknown']

SPECIFICATIONS_OUTPUT_RECORDING_TYPE_VALUES: set[SpecificationsOutputRecordingType] = { 'cmr', 'smr', 'unknown',  }

def check_specifications_output_recording_type(value: str) -> SpecificationsOutputRecordingType:
    if value in SPECIFICATIONS_OUTPUT_RECORDING_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_OUTPUT_RECORDING_TYPE_VALUES!r}")
