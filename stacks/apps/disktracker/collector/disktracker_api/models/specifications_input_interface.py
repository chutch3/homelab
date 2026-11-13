from typing import Literal

SpecificationsInputInterface = Literal['nvme_pcie', 'sas', 'sata', 'unknown', 'usb']

SPECIFICATIONS_INPUT_INTERFACE_VALUES: set[SpecificationsInputInterface] = { 'nvme_pcie', 'sas', 'sata', 'unknown', 'usb',  }

def check_specifications_input_interface(value: str) -> SpecificationsInputInterface:
    if value in SPECIFICATIONS_INPUT_INTERFACE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_INPUT_INTERFACE_VALUES!r}")
