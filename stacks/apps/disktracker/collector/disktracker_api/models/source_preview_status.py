from typing import Literal

SourcePreviewStatus = Literal['failed', 'found', 'nothing']

SOURCE_PREVIEW_STATUS_VALUES: set[SourcePreviewStatus] = { 'failed', 'found', 'nothing',  }

def check_source_preview_status(value: str) -> SourcePreviewStatus:
    if value in SOURCE_PREVIEW_STATUS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SOURCE_PREVIEW_STATUS_VALUES!r}")
