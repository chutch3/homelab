from typing import Literal

SpecificationsEditMediaType = Literal['flash_card', 'hdd', 'ssd', 'unknown']

SPECIFICATIONS_EDIT_MEDIA_TYPE_VALUES: set[SpecificationsEditMediaType] = { 'flash_card', 'hdd', 'ssd', 'unknown',  }

def check_specifications_edit_media_type(value: str) -> SpecificationsEditMediaType:
    if value in SPECIFICATIONS_EDIT_MEDIA_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_EDIT_MEDIA_TYPE_VALUES!r}")
