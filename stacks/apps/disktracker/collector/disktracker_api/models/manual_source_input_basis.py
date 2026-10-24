from typing import Literal

ManualSourceInputBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

MANUAL_SOURCE_INPUT_BASIS_VALUES: set[ManualSourceInputBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_manual_source_input_basis(value: str) -> ManualSourceInputBasis:
    if value in MANUAL_SOURCE_INPUT_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MANUAL_SOURCE_INPUT_BASIS_VALUES!r}")
