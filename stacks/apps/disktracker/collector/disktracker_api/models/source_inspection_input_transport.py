from typing import Literal

SourceInspectionInputTransport = Literal['browser', 'direct']

SOURCE_INSPECTION_INPUT_TRANSPORT_VALUES: set[SourceInspectionInputTransport] = { 'browser', 'direct',  }

def check_source_inspection_input_transport(value: str) -> SourceInspectionInputTransport:
    if value in SOURCE_INSPECTION_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SOURCE_INSPECTION_INPUT_TRANSPORT_VALUES!r}")
