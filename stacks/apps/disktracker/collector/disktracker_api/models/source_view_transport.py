from typing import Literal

SourceViewTransport = Literal['browser', 'direct']

SOURCE_VIEW_TRANSPORT_VALUES: set[SourceViewTransport] = { 'browser', 'direct',  }

def check_source_view_transport(value: str) -> SourceViewTransport:
    if value in SOURCE_VIEW_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SOURCE_VIEW_TRANSPORT_VALUES!r}")
