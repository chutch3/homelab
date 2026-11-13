from typing import Literal

MarketInterfaceType0 = Literal['nvme_pcie', 'sas', 'sata', 'unknown', 'usb']

MARKET_INTERFACE_TYPE_0_VALUES: set[MarketInterfaceType0] = { 'nvme_pcie', 'sas', 'sata', 'unknown', 'usb',  }

def check_market_interface_type_0(value: str) -> MarketInterfaceType0:
    if value in MARKET_INTERFACE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MARKET_INTERFACE_TYPE_0_VALUES!r}")
