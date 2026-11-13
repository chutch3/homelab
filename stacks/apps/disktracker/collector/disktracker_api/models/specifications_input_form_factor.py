from typing import Literal

SpecificationsInputFormFactor = Literal['2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown']

SPECIFICATIONS_INPUT_FORM_FACTOR_VALUES: set[SpecificationsInputFormFactor] = { '2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown',  }

def check_specifications_input_form_factor(value: str) -> SpecificationsInputFormFactor:
    if value in SPECIFICATIONS_INPUT_FORM_FACTOR_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_INPUT_FORM_FACTOR_VALUES!r}")
