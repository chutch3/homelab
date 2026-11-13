from typing import Literal

ShopifySourceViewTransport = Literal['browser', 'direct']

SHOPIFY_SOURCE_VIEW_TRANSPORT_VALUES: set[ShopifySourceViewTransport] = { 'browser', 'direct',  }

def check_shopify_source_view_transport(value: str) -> ShopifySourceViewTransport:
    if value in SHOPIFY_SOURCE_VIEW_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SHOPIFY_SOURCE_VIEW_TRANSPORT_VALUES!r}")
