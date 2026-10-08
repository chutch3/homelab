from typing import Literal

SpecificationsMediaType = Literal['flash_card', 'hdd', 'ssd', 'unknown']

SPECIFICATIONS_MEDIA_TYPE_VALUES: set[SpecificationsMediaType] = { 'flash_card', 'hdd', 'ssd', 'unknown',  }

def check_specifications_media_type(value: str) -> SpecificationsMediaType:
    if value in SPECIFICATIONS_MEDIA_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_MEDIA_TYPE_VALUES!r}")
