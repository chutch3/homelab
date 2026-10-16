from typing import Literal

PriceTrendsInterfaceType0 = Literal['nvme_pcie', 'sas', 'sata', 'unknown', 'usb']

PRICE_TRENDS_INTERFACE_TYPE_0_VALUES: set[PriceTrendsInterfaceType0] = { 'nvme_pcie', 'sas', 'sata', 'unknown', 'usb',  }

def check_price_trends_interface_type_0(value: str) -> PriceTrendsInterfaceType0:
    if value in PRICE_TRENDS_INTERFACE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICE_TRENDS_INTERFACE_TYPE_0_VALUES!r}")
