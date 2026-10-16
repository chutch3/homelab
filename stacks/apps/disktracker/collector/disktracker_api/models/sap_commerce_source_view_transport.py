from typing import Literal

SapCommerceSourceViewTransport = Literal['browser', 'direct']

SAP_COMMERCE_SOURCE_VIEW_TRANSPORT_VALUES: set[SapCommerceSourceViewTransport] = { 'browser', 'direct',  }

def check_sap_commerce_source_view_transport(value: str) -> SapCommerceSourceViewTransport:
    if value in SAP_COMMERCE_SOURCE_VIEW_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SAP_COMMERCE_SOURCE_VIEW_TRANSPORT_VALUES!r}")
