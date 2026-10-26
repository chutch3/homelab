from typing import Literal

ShopifySourceViewBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SHOPIFY_SOURCE_VIEW_BASIS_VALUES: set[ShopifySourceViewBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_shopify_source_view_basis(value: str) -> ShopifySourceViewBasis:
    if value in SHOPIFY_SOURCE_VIEW_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SHOPIFY_SOURCE_VIEW_BASIS_VALUES!r}")
