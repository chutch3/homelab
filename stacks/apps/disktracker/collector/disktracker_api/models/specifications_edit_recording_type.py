from typing import Literal

SpecificationsEditRecordingType = Literal['cmr', 'smr', 'unknown']

SPECIFICATIONS_EDIT_RECORDING_TYPE_VALUES: set[SpecificationsEditRecordingType] = { 'cmr', 'smr', 'unknown',  }

def check_specifications_edit_recording_type(value: str) -> SpecificationsEditRecordingType:
    if value in SPECIFICATIONS_EDIT_RECORDING_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_EDIT_RECORDING_TYPE_VALUES!r}")
