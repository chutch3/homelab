from typing import Literal

SourceInputTransport = Literal['browser', 'direct']

SOURCE_INPUT_TRANSPORT_VALUES: set[SourceInputTransport] = { 'browser', 'direct',  }

def check_source_input_transport(value: str) -> SourceInputTransport:
    if value in SOURCE_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SOURCE_INPUT_TRANSPORT_VALUES!r}")
