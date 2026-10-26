from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.match_decision_condition import check_match_decision_condition
from ..models.match_decision_condition import MatchDecisionCondition
from typing import cast
from typing import Literal, cast
from uuid import UUID






T = TypeVar("T", bound="MatchDecision")



@_attrs_define
class MatchDecision:
    """ A reviewer's decision that a queued offer is this drive (one already recorded) in this
    condition: its price is recorded, and later prices of it are matched the same way. It never
    says what the drive is: a drive is made (POST /drives) or corrected (PATCH /drives/{id})
    beforehand.

        Attributes:
            condition (MatchDecisionCondition):
            decision (Literal['match']):
            drive_id (UUID):
     """

    condition: MatchDecisionCondition
    decision: Literal['match']
    drive_id: UUID





    def to_dict(self) -> dict[str, Any]:
        condition: str = self.condition

        decision = self.decision

        drive_id = str(self.drive_id)


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "condition": condition,
            "decision": decision,
            "drive_id": drive_id,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        condition = check_match_decision_condition(d.pop("condition"))




        decision = cast(Literal['match'] , d.pop("decision"))
        if decision != 'match':
            raise ValueError(f"decision must match const 'match', got '{decision}'")

        drive_id = UUID(d.pop("drive_id"))




        match_decision = cls(
            condition=condition,
            decision=decision,
            drive_id=drive_id,
        )

        return match_decision
