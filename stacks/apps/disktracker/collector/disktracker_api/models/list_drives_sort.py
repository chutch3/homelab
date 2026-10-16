from typing import Literal

ListDrivesSort = Literal['capacity-asc', 'capacity-desc', 'checked-asc', 'checked-desc', 'total-asc', 'total-desc', 'unit-asc', 'unit-desc']

LIST_DRIVES_SORT_VALUES: set[ListDrivesSort] = { 'capacity-asc', 'capacity-desc', 'checked-asc', 'checked-desc', 'total-asc', 'total-desc', 'unit-asc', 'unit-desc',  }

def check_list_drives_sort(value: str) -> ListDrivesSort:
    if value in LIST_DRIVES_SORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_DRIVES_SORT_VALUES!r}")
