from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast






T = TypeVar("T", bound="ShopifySettingsOutput")



@_attrs_define
class ShopifySettingsOutput:
    """
        Attributes:
            collections (list[str]):
            free_shipping (bool):  Default: False.
     """

    collections: list[str]
    free_shipping: bool = False





    def to_dict(self) -> dict[str, Any]:
        collections = self.collections



        free_shipping = self.free_shipping


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "collections": collections,
            "free_shipping": free_shipping,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        collections = cast(list[str], d.pop("collections"))


        free_shipping = d.pop("free_shipping")

        shopify_settings_output = cls(
            collections=collections,
            free_shipping=free_shipping,
        )

        return shopify_settings_output
