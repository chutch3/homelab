from typing import Literal

SpecificationsFormFactor = Literal['2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown']

SPECIFICATIONS_FORM_FACTOR_VALUES: set[SpecificationsFormFactor] = { '2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown',  }

def check_specifications_form_factor(value: str) -> SpecificationsFormFactor:
    if value in SPECIFICATIONS_FORM_FACTOR_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_FORM_FACTOR_VALUES!r}")
