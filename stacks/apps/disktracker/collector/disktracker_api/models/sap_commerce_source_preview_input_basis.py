from typing import Literal

SapCommerceSourcePreviewInputBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SAP_COMMERCE_SOURCE_PREVIEW_INPUT_BASIS_VALUES: set[SapCommerceSourcePreviewInputBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_sap_commerce_source_preview_input_basis(value: str) -> SapCommerceSourcePreviewInputBasis:
    if value in SAP_COMMERCE_SOURCE_PREVIEW_INPUT_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SAP_COMMERCE_SOURCE_PREVIEW_INPUT_BASIS_VALUES!r}")
