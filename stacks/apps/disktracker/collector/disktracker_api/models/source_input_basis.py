from typing import Literal

SourceInputBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SOURCE_INPUT_BASIS_VALUES: set[SourceInputBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_source_input_basis(value: str) -> SourceInputBasis:
    if value in SOURCE_INPUT_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SOURCE_INPUT_BASIS_VALUES!r}")
