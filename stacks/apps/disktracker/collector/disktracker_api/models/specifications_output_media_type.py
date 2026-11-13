from typing import Literal

SpecificationsOutputMediaType = Literal['flash_card', 'hdd', 'ssd', 'unknown']

SPECIFICATIONS_OUTPUT_MEDIA_TYPE_VALUES: set[SpecificationsOutputMediaType] = { 'flash_card', 'hdd', 'ssd', 'unknown',  }

def check_specifications_output_media_type(value: str) -> SpecificationsOutputMediaType:
    if value in SPECIFICATIONS_OUTPUT_MEDIA_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_OUTPUT_MEDIA_TYPE_VALUES!r}")
