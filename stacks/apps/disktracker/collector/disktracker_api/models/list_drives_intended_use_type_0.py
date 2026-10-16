from typing import Literal

ListDrivesIntendedUseType0 = Literal['archive', 'desktop', 'enterprise', 'nas', 'surveillance']

LIST_DRIVES_INTENDED_USE_TYPE_0_VALUES: set[ListDrivesIntendedUseType0] = { 'archive', 'desktop', 'enterprise', 'nas', 'surveillance',  }

def check_list_drives_intended_use_type_0(value: str) -> ListDrivesIntendedUseType0:
    if value in LIST_DRIVES_INTENDED_USE_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_DRIVES_INTENDED_USE_TYPE_0_VALUES!r}")
