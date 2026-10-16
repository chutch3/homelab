from typing import Literal

ListDrivesRecordingTypeType0 = Literal['cmr', 'smr', 'unknown']

LIST_DRIVES_RECORDING_TYPE_TYPE_0_VALUES: set[ListDrivesRecordingTypeType0] = { 'cmr', 'smr', 'unknown',  }

def check_list_drives_recording_type_type_0(value: str) -> ListDrivesRecordingTypeType0:
    if value in LIST_DRIVES_RECORDING_TYPE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_DRIVES_RECORDING_TYPE_TYPE_0_VALUES!r}")
