from typing import Literal

ShopifySourcePreviewInputTransport = Literal['browser', 'direct']

SHOPIFY_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES: set[ShopifySourcePreviewInputTransport] = { 'browser', 'direct',  }

def check_shopify_source_preview_input_transport(value: str) -> ShopifySourcePreviewInputTransport:
    if value in SHOPIFY_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SHOPIFY_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES!r}")
