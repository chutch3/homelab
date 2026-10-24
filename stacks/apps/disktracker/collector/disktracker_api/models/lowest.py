from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from uuid import UUID






T = TypeVar("T", bound="Lowest")



@_attrs_define
class Lowest:
    """ The offers with the lowest total and the lowest total per terabyte among every offer that
    matches, in stock and checked recently.

        Attributes:
            total (list[UUID]):
            unit (list[UUID]):
     """

    total: list[UUID]
    unit: list[UUID]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        total = []
        for total_item_data in self.total:
            total_item = str(total_item_data)
            total.append(total_item)



        unit = []
        for unit_item_data in self.unit:
            unit_item = str(unit_item_data)
            unit.append(unit_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "total": total,
            "unit": unit,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        total = []
        _total = d.pop("total")
        for total_item_data in (_total):
            total_item = UUID(total_item_data)



            total.append(total_item)


        unit = []
        _unit = d.pop("unit")
        for unit_item_data in (_unit):
            unit_item = UUID(unit_item_data)



            unit.append(unit_item)


        lowest = cls(
            total=total,
            unit=unit,
        )


        lowest.additional_properties = d
        return lowest

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
