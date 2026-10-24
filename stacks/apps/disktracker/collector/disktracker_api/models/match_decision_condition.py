from typing import Literal

MatchDecisionCondition = Literal['manufacturer_recertified', 'new', 'refurbished', 'used']

MATCH_DECISION_CONDITION_VALUES: set[MatchDecisionCondition] = { 'manufacturer_recertified', 'new', 'refurbished', 'used',  }

def check_match_decision_condition(value: str) -> MatchDecisionCondition:
    if value in MATCH_DECISION_CONDITION_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {MATCH_DECISION_CONDITION_VALUES!r}")
