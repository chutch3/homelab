from typing import Literal

ShopifySourceInputTransport = Literal['browser', 'direct']

SHOPIFY_SOURCE_INPUT_TRANSPORT_VALUES: set[ShopifySourceInputTransport] = { 'browser', 'direct',  }

def check_shopify_source_input_transport(value: str) -> ShopifySourceInputTransport:
    if value in SHOPIFY_SOURCE_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SHOPIFY_SOURCE_INPUT_TRANSPORT_VALUES!r}")
