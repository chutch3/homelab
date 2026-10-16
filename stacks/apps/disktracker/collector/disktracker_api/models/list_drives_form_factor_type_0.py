from typing import Literal

ListDrivesFormFactorType0 = Literal['2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown']

LIST_DRIVES_FORM_FACTOR_TYPE_0_VALUES: set[ListDrivesFormFactorType0] = { '2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown',  }

def check_list_drives_form_factor_type_0(value: str) -> ListDrivesFormFactorType0:
    if value in LIST_DRIVES_FORM_FACTOR_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_DRIVES_FORM_FACTOR_TYPE_0_VALUES!r}")
