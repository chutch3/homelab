from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset







T = TypeVar("T", bound="DriveIssueCounts")



@_attrs_define
class DriveIssueCounts:
    """
        Attributes:
            stale (int):
            unknown_specifications (int):
     """

    stale: int
    unknown_specifications: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        stale = self.stale

        unknown_specifications = self.unknown_specifications


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "stale": stale,
            "unknown_specifications": unknown_specifications,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        stale = d.pop("stale")

        unknown_specifications = d.pop("unknown_specifications")

        drive_issue_counts = cls(
            stale=stale,
            unknown_specifications=unknown_specifications,
        )


        drive_issue_counts.additional_properties = d
        return drive_issue_counts

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
