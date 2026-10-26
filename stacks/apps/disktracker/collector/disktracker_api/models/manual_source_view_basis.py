from typing import Literal

ManualSourceViewBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

MANUAL_SOURCE_VIEW_BASIS_VALUES: set[ManualSourceViewBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_manual_source_view_basis(value: str) -> ManualSourceViewBasis:
    if value in MANUAL_SOURCE_VIEW_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MANUAL_SOURCE_VIEW_BASIS_VALUES!r}")
