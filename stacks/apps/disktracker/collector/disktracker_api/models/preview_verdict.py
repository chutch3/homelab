from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.preview_verdict_outcome import check_preview_verdict_outcome
from ..models.preview_verdict_outcome import PreviewVerdictOutcome
from typing import cast






T = TypeVar("T", bound="PreviewVerdict")



@_attrs_define
class PreviewVerdict:
    """ What disktracker would do with the offer: record it, hold it for review, or ignore it.

        Attributes:
            outcome (PreviewVerdictOutcome):
            reason (None | str):
     """

    outcome: PreviewVerdictOutcome
    reason: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        outcome: str = self.outcome

        reason: None | str
        reason = self.reason


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "outcome": outcome,
            "reason": reason,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        outcome = check_preview_verdict_outcome(d.pop("outcome"))




        def _parse_reason(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        reason = _parse_reason(d.pop("reason"))


        preview_verdict = cls(
            outcome=outcome,
            reason=reason,
        )


        preview_verdict.additional_properties = d
        return preview_verdict

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
