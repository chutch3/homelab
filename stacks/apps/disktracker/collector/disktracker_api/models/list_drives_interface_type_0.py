from typing import Literal

ListDrivesInterfaceType0 = Literal['nvme_pcie', 'sas', 'sata', 'unknown', 'usb']

LIST_DRIVES_INTERFACE_TYPE_0_VALUES: set[ListDrivesInterfaceType0] = { 'nvme_pcie', 'sas', 'sata', 'unknown', 'usb',  }

def check_list_drives_interface_type_0(value: str) -> ListDrivesInterfaceType0:
    if value in LIST_DRIVES_INTERFACE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_DRIVES_INTERFACE_TYPE_0_VALUES!r}")
