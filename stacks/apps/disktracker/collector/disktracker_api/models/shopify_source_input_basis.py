from typing import Literal

ShopifySourceInputBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SHOPIFY_SOURCE_INPUT_BASIS_VALUES: set[ShopifySourceInputBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_shopify_source_input_basis(value: str) -> ShopifySourceInputBasis:
    if value in SHOPIFY_SOURCE_INPUT_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SHOPIFY_SOURCE_INPUT_BASIS_VALUES!r}")
