from typing import Literal

ManualSourcePreviewInputTransport = Literal['browser', 'direct']

MANUAL_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES: set[ManualSourcePreviewInputTransport] = { 'browser', 'direct',  }

def check_manual_source_preview_input_transport(value: str) -> ManualSourcePreviewInputTransport:
    if value in MANUAL_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MANUAL_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES!r}")
