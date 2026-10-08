from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset







T = TypeVar("T", bound="ListingText")



@_attrs_define
class ListingText:
    """ Text a person copied from a listing page.

        Attributes:
            text (str):
     """

    text: str





    def to_dict(self) -> dict[str, Any]:
        text = self.text


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "text": text,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        text = d.pop("text")

        listing_text = cls(
            text=text,
        )

        return listing_text
