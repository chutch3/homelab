from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.match_decision_condition import check_match_decision_condition
from ..models.match_decision_condition import MatchDecisionCondition
from ..types import UNSET, Unset
from typing import cast
from typing import Literal, cast






T = TypeVar("T", bound="MatchDecision")



@_attrs_define
class MatchDecision:
    """ A reviewer's decision that a queued offer is this drive in this condition: its price is
    recorded, and later prices of it are matched the same way. capacity_gb: the drive's, needed
    when the MPN is new; left out, a drive already recorded keeps its own. correct_drive: the
    drive recorded has the wrong capacity, and is corrected to capacity_gb, for every offer of
    it.

        Attributes:
            condition (MatchDecisionCondition):
            decision (Literal['match']):
            mpn (str):
            capacity_gb (int | None | Unset):
            correct_drive (bool | Unset):  Default: False.
     """

    condition: MatchDecisionCondition
    decision: Literal['match']
    mpn: str
    capacity_gb: int | None | Unset = UNSET
    correct_drive: bool | Unset = False





    def to_dict(self) -> dict[str, Any]:
        condition: str = self.condition

        decision = self.decision

        mpn = self.mpn

        capacity_gb: int | None | Unset
        if isinstance(self.capacity_gb, Unset):
            capacity_gb = UNSET
        else:
            capacity_gb = self.capacity_gb

        correct_drive = self.correct_drive


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "condition": condition,
            "decision": decision,
            "mpn": mpn,
        })
        if capacity_gb is not UNSET:
            field_dict["capacity_gb"] = capacity_gb
        if correct_drive is not UNSET:
            field_dict["correct_drive"] = correct_drive

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        condition = check_match_decision_condition(d.pop("condition"))




        decision = cast(Literal['match'] , d.pop("decision"))
        if decision != 'match':
            raise ValueError(f"decision must match const 'match', got '{decision}'")

        mpn = d.pop("mpn")

        def _parse_capacity_gb(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        capacity_gb = _parse_capacity_gb(d.pop("capacity_gb", UNSET))


        correct_drive = d.pop("correct_drive", UNSET)

        match_decision = cls(
            condition=condition,
            decision=decision,
            mpn=mpn,
            capacity_gb=capacity_gb,
            correct_drive=correct_drive,
        )

        return match_decision
