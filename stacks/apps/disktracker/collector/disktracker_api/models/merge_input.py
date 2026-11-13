from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from uuid import UUID






T = TypeVar("T", bound="MergeInput")



@_attrs_define
class MergeInput:
    """ The drive another is merged into: it survives.

        Attributes:
            target_drive_id (UUID):
     """

    target_drive_id: UUID





    def to_dict(self) -> dict[str, Any]:
        target_drive_id = str(self.target_drive_id)


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "target_drive_id": target_drive_id,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        target_drive_id = UUID(d.pop("target_drive_id"))




        merge_input = cls(
            target_drive_id=target_drive_id,
        )

        return merge_input
