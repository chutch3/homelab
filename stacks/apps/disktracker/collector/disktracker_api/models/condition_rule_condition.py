from typing import Literal

ConditionRuleCondition = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

CONDITION_RULE_CONDITION_VALUES: set[ConditionRuleCondition] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_condition_rule_condition(value: str) -> ConditionRuleCondition:
    if value in CONDITION_RULE_CONDITION_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {CONDITION_RULE_CONDITION_VALUES!r}")
