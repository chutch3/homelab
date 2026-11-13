from typing import Literal

IngestionInputConditionType0 = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

INGESTION_INPUT_CONDITION_TYPE_0_VALUES: set[IngestionInputConditionType0] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_ingestion_input_condition_type_0(value: str) -> IngestionInputConditionType0:
    if value in INGESTION_INPUT_CONDITION_TYPE_0_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {INGESTION_INPUT_CONDITION_TYPE_0_VALUES!r}")
