from typing import Literal

ScrapedInputConditionType0 = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

SCRAPED_INPUT_CONDITION_TYPE_0_VALUES: set[ScrapedInputConditionType0] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_scraped_input_condition_type_0(value: str) -> ScrapedInputConditionType0:
    if value in SCRAPED_INPUT_CONDITION_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SCRAPED_INPUT_CONDITION_TYPE_0_VALUES!r}")
