from typing import Literal

SapCommerceSourcePreviewInputTransport = Literal['browser', 'direct']

SAP_COMMERCE_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES: set[SapCommerceSourcePreviewInputTransport] = { 'browser', 'direct',  }

def check_sap_commerce_source_preview_input_transport(value: str) -> SapCommerceSourcePreviewInputTransport:
    if value in SAP_COMMERCE_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SAP_COMMERCE_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES!r}")
