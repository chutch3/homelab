from typing import Literal

SpecificationsEditFormFactor = Literal['2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown']

SPECIFICATIONS_EDIT_FORM_FACTOR_VALUES: set[SpecificationsEditFormFactor] = { '2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown',  }

def check_specifications_edit_form_factor(value: str) -> SpecificationsEditFormFactor:
    if value in SPECIFICATIONS_EDIT_FORM_FACTOR_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_EDIT_FORM_FACTOR_VALUES!r}")
