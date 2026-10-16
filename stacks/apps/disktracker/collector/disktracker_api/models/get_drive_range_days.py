from typing import Literal

GetDriveRangeDays = Literal[30, 90, 180]

GET_DRIVE_RANGE_DAYS_VALUES: set[GetDriveRangeDays] = { 30, 90, 180,  }

def check_get_drive_range_days(value: int) -> GetDriveRangeDays:
    if value in GET_DRIVE_RANGE_DAYS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {GET_DRIVE_RANGE_DAYS_VALUES!r}")
