from typing import Literal

ManualSourcePreviewInputBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

MANUAL_SOURCE_PREVIEW_INPUT_BASIS_VALUES: set[ManualSourcePreviewInputBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_manual_source_preview_input_basis(value: str) -> ManualSourcePreviewInputBasis:
    if value in MANUAL_SOURCE_PREVIEW_INPUT_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MANUAL_SOURCE_PREVIEW_INPUT_BASIS_VALUES!r}")
