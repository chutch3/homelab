from typing import Literal

SpecificationsOutputFormFactor = Literal['2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown']

SPECIFICATIONS_OUTPUT_FORM_FACTOR_VALUES: set[SpecificationsOutputFormFactor] = { '2_5', '3_5', 'm_2', 'microsd', 'sd', 'unknown',  }

def check_specifications_output_form_factor(value: str) -> SpecificationsOutputFormFactor:
    if value in SPECIFICATIONS_OUTPUT_FORM_FACTOR_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SPECIFICATIONS_OUTPUT_FORM_FACTOR_VALUES!r}")
