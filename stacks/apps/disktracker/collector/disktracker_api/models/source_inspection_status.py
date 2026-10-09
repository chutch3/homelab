from typing import Literal

SourceInspectionStatus = Literal['failed', 'found', 'nothing']

SOURCE_INSPECTION_STATUS_VALUES: set[SourceInspectionStatus] = { 'failed', 'found', 'nothing',  }

def check_source_inspection_status(value: str) -> SourceInspectionStatus:
    if value in SOURCE_INSPECTION_STATUS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SOURCE_INSPECTION_STATUS_VALUES!r}")
