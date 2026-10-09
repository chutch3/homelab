from typing import Literal

SourcePreviewInputTransport = Literal['browser', 'direct']

SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES: set[SourcePreviewInputTransport] = { 'browser', 'direct',  }

def check_source_preview_input_transport(value: str) -> SourcePreviewInputTransport:
    if value in SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES!r}")
