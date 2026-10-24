from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.choice_literalnew_manufacturer_recertified_refurbished_used_value import check_choice_literalnew_manufacturer_recertified_refurbished_used_value
from ..models.choice_literalnew_manufacturer_recertified_refurbished_used_value import ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsedValue
from typing import cast






T = TypeVar("T", bound="ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsed")



@_attrs_define
class ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsed:
    """
        Attributes:
            drives (int):
            value (ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsedValue):
     """

    drives: int
    value: ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsedValue
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        drives = self.drives

        value: str = self.value


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "drives": drives,
            "value": value,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        drives = d.pop("drives")

        value = check_choice_literalnew_manufacturer_recertified_refurbished_used_value(d.pop("value"))




        choice_literalnew_manufacturer_recertified_refurbished_used = cls(
            drives=drives,
            value=value,
        )


        choice_literalnew_manufacturer_recertified_refurbished_used.additional_properties = d
        return choice_literalnew_manufacturer_recertified_refurbished_used

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
