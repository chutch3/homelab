from typing import Literal

SourceViewBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SOURCE_VIEW_BASIS_VALUES: set[SourceViewBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_source_view_basis(value: str) -> SourceViewBasis:
    if value in SOURCE_VIEW_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SOURCE_VIEW_BASIS_VALUES!r}")
