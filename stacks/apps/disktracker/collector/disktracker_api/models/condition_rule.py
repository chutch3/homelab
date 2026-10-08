from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.condition_rule_condition import check_condition_rule_condition
from ..models.condition_rule_condition import ConditionRuleCondition
from typing import cast






T = TypeVar("T", bound="ConditionRule")



@_attrs_define
class ConditionRule:
    """ Text matching the pattern (a case-insensitive regular expression) names the condition;
    rules are read in order and the first match wins.

        Attributes:
            condition (ConditionRuleCondition):
            pattern (str):
     """

    condition: ConditionRuleCondition
    pattern: str





    def to_dict(self) -> dict[str, Any]:
        condition: str = self.condition

        pattern = self.pattern


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "condition": condition,
            "pattern": pattern,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        condition = check_condition_rule_condition(d.pop("condition"))




        pattern = d.pop("pattern")

        condition_rule = cls(
            condition=condition,
            pattern=pattern,
        )

        return condition_rule
