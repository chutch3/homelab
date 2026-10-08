from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset







T = TypeVar("T", bound="AliasInput")



@_attrs_define
class AliasInput:
    """
        Attributes:
            mpn (str):
     """

    mpn: str





    def to_dict(self) -> dict[str, Any]:
        mpn = self.mpn


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "mpn": mpn,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        mpn = d.pop("mpn")

        alias_input = cls(
            mpn=mpn,
        )

        return alias_input
