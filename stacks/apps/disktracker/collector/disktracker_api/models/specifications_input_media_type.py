from typing import Literal

SpecificationsInputMediaType = Literal['flash_card', 'hdd', 'ssd', 'unknown']

SPECIFICATIONS_INPUT_MEDIA_TYPE_VALUES: set[SpecificationsInputMediaType] = { 'flash_card', 'hdd', 'ssd', 'unknown',  }

def check_specifications_input_media_type(value: str) -> SpecificationsInputMediaType:
    if value in SPECIFICATIONS_INPUT_MEDIA_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_INPUT_MEDIA_TYPE_VALUES!r}")
