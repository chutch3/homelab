from typing import Literal

SpecificationsOutputInterface = Literal['nvme_pcie', 'sas', 'sata', 'unknown', 'usb']

SPECIFICATIONS_OUTPUT_INTERFACE_VALUES: set[SpecificationsOutputInterface] = { 'nvme_pcie', 'sas', 'sata', 'unknown', 'usb',  }

def check_specifications_output_interface(value: str) -> SpecificationsOutputInterface:
    if value in SPECIFICATIONS_OUTPUT_INTERFACE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_OUTPUT_INTERFACE_VALUES!r}")
