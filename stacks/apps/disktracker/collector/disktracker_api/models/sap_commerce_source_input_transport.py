from typing import Literal

SapCommerceSourceInputTransport = Literal['browser', 'direct']

SAP_COMMERCE_SOURCE_INPUT_TRANSPORT_VALUES: set[SapCommerceSourceInputTransport] = { 'browser', 'direct',  }

def check_sap_commerce_source_input_transport(value: str) -> SapCommerceSourceInputTransport:
    if value in SAP_COMMERCE_SOURCE_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SAP_COMMERCE_SOURCE_INPUT_TRANSPORT_VALUES!r}")
