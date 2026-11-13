from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.price_mark_condition import check_price_mark_condition
from ..models.price_mark_condition import PriceMarkCondition
from typing import cast
from uuid import UUID






T = TypeVar("T", bound="PriceMark")



@_attrs_define
class PriceMark:
    """ A drive in one condition, placed by the lowest item price per terabyte any store with it
    in stock asks today, in cents. lowest marks the cheapest of those checked recently.

        Attributes:
            capacity_gb (int):
            condition (PriceMarkCondition):
            drive_id (UUID):
            lowest (bool):
            per_tb_cents (int): Lowest in-stock item price per decimal TB, in US cents; shipping excluded.
            title (str):
     """

    capacity_gb: int
    condition: PriceMarkCondition
    drive_id: UUID
    lowest: bool
    per_tb_cents: int
    title: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        capacity_gb = self.capacity_gb

        condition: str = self.condition

        drive_id = str(self.drive_id)

        lowest = self.lowest

        per_tb_cents = self.per_tb_cents

        title = self.title


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "capacity_gb": capacity_gb,
            "condition": condition,
            "drive_id": drive_id,
            "lowest": lowest,
            "per_tb_cents": per_tb_cents,
            "title": title,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        capacity_gb = d.pop("capacity_gb")

        condition = check_price_mark_condition(d.pop("condition"))




        drive_id = UUID(d.pop("drive_id"))




        lowest = d.pop("lowest")

        per_tb_cents = d.pop("per_tb_cents")

        title = d.pop("title")

        price_mark = cls(
            capacity_gb=capacity_gb,
            condition=condition,
            drive_id=drive_id,
            lowest=lowest,
            per_tb_cents=per_tb_cents,
            title=title,
        )


        price_mark.additional_properties = d
        return price_mark

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
