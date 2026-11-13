from typing import Literal

ShopifySourcePreviewInputBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SHOPIFY_SOURCE_PREVIEW_INPUT_BASIS_VALUES: set[ShopifySourcePreviewInputBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_shopify_source_preview_input_basis(value: str) -> ShopifySourcePreviewInputBasis:
    if value in SHOPIFY_SOURCE_PREVIEW_INPUT_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SHOPIFY_SOURCE_PREVIEW_INPUT_BASIS_VALUES!r}")
