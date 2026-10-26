from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import Literal, cast






T = TypeVar("T", bound="IgnoreDecision")



@_attrs_define
class IgnoreDecision:
    """ A reviewer's decision that a queued offer is nothing to track: later prices of it are
    ignored.

        Attributes:
            decision (Literal['ignore']):
     """

    decision: Literal['ignore']





    def to_dict(self) -> dict[str, Any]:
        decision = self.decision


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "decision": decision,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        decision = cast(Literal['ignore'] , d.pop("decision"))
        if decision != 'ignore':
            raise ValueError(f"decision must match const 'ignore', got '{decision}'")

        ignore_decision = cls(
            decision=decision,
        )

        return ignore_decision
