from typing import Literal

PricesTodayInterfaceType0 = Literal['nvme_pcie', 'sas', 'sata', 'unknown', 'usb']

PRICES_TODAY_INTERFACE_TYPE_0_VALUES: set[PricesTodayInterfaceType0] = { 'nvme_pcie', 'sas', 'sata', 'unknown', 'usb',  }

def check_prices_today_interface_type_0(value: str) -> PricesTodayInterfaceType0:
    if value in PRICES_TODAY_INTERFACE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {PRICES_TODAY_INTERFACE_TYPE_0_VALUES!r}")
