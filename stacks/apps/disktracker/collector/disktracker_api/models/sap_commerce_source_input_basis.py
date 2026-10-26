from typing import Literal

SapCommerceSourceInputBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SAP_COMMERCE_SOURCE_INPUT_BASIS_VALUES: set[SapCommerceSourceInputBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_sap_commerce_source_input_basis(value: str) -> SapCommerceSourceInputBasis:
    if value in SAP_COMMERCE_SOURCE_INPUT_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SAP_COMMERCE_SOURCE_INPUT_BASIS_VALUES!r}")
