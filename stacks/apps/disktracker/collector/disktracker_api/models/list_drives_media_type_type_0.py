from typing import Literal

ListDrivesMediaTypeType0 = Literal['flash_card', 'hdd', 'ssd', 'unknown']

LIST_DRIVES_MEDIA_TYPE_TYPE_0_VALUES: set[ListDrivesMediaTypeType0] = { 'flash_card', 'hdd', 'ssd', 'unknown',  }

def check_list_drives_media_type_type_0(value: str) -> ListDrivesMediaTypeType0:
    if value in LIST_DRIVES_MEDIA_TYPE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_DRIVES_MEDIA_TYPE_TYPE_0_VALUES!r}")
