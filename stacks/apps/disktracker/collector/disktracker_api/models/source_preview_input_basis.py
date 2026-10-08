from typing import Literal

SourcePreviewInputBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SOURCE_PREVIEW_INPUT_BASIS_VALUES: set[SourcePreviewInputBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_source_preview_input_basis(value: str) -> SourcePreviewInputBasis:
    if value in SOURCE_PREVIEW_INPUT_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SOURCE_PREVIEW_INPUT_BASIS_VALUES!r}")
