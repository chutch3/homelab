from typing import Literal

SapCommerceSourceViewBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SAP_COMMERCE_SOURCE_VIEW_BASIS_VALUES: set[SapCommerceSourceViewBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_sap_commerce_source_view_basis(value: str) -> SapCommerceSourceViewBasis:
    if value in SAP_COMMERCE_SOURCE_VIEW_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SAP_COMMERCE_SOURCE_VIEW_BASIS_VALUES!r}")
