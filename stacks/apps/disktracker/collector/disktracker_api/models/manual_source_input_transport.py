from typing import Literal

ManualSourceInputTransport = Literal['browser', 'direct']

MANUAL_SOURCE_INPUT_TRANSPORT_VALUES: set[ManualSourceInputTransport] = { 'browser', 'direct',  }

def check_manual_source_input_transport(value: str) -> ManualSourceInputTransport:
    if value in MANUAL_SOURCE_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MANUAL_SOURCE_INPUT_TRANSPORT_VALUES!r}")
