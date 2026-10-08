from typing import Literal

SpecificationsInterface = Literal['nvme_pcie', 'sas', 'sata', 'unknown', 'usb']

SPECIFICATIONS_INTERFACE_VALUES: set[SpecificationsInterface] = { 'nvme_pcie', 'sas', 'sata', 'unknown', 'usb',  }

def check_specifications_interface(value: str) -> SpecificationsInterface:
    if value in SPECIFICATIONS_INTERFACE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_INTERFACE_VALUES!r}")
