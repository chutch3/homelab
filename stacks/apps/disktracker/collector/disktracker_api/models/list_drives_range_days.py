from typing import Literal

ListDrivesRangeDays = Literal[30, 90, 180]

LIST_DRIVES_RANGE_DAYS_VALUES: set[ListDrivesRangeDays] = { 30, 90, 180,  }

def check_list_drives_range_days(value: int) -> ListDrivesRangeDays:
    if value in LIST_DRIVES_RANGE_DAYS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_DRIVES_RANGE_DAYS_VALUES!r}")
