from typing import Literal

ManualSourceViewTransport = Literal['browser', 'direct']

MANUAL_SOURCE_VIEW_TRANSPORT_VALUES: set[ManualSourceViewTransport] = { 'browser', 'direct',  }

def check_manual_source_view_transport(value: str) -> ManualSourceViewTransport:
    if value in MANUAL_SOURCE_VIEW_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MANUAL_SOURCE_VIEW_TRANSPORT_VALUES!r}")
