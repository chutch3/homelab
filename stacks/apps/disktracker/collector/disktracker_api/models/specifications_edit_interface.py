from typing import Literal

SpecificationsEditInterface = Literal['nvme_pcie', 'sas', 'sata', 'unknown', 'usb']

SPECIFICATIONS_EDIT_INTERFACE_VALUES: set[SpecificationsEditInterface] = { 'nvme_pcie', 'sas', 'sata', 'unknown', 'usb',  }

def check_specifications_edit_interface(value: str) -> SpecificationsEditInterface:
    if value in SPECIFICATIONS_EDIT_INTERFACE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_EDIT_INTERFACE_VALUES!r}")
