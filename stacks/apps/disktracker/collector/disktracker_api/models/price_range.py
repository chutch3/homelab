from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast






T = TypeVar("T", bound="PriceRange")



@_attrs_define
class PriceRange:
    """ Where a drive's lowest item price has been over the days asked for, in cents: today's
    (null when no store has it in stock), the lowest and highest it has been, its average weighed
    by how long each price held, and how many days of prices there are.

        Attributes:
            average (int):
            days (int):
            high (int):
            low (int):
            today (int | None):
     """

    average: int
    days: int
    high: int
    low: int
    today: int | None
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        average = self.average

        days = self.days

        high = self.high

        low = self.low

        today: int | None
        today = self.today


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "average": average,
            "days": days,
            "high": high,
            "low": low,
            "today": today,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        average = d.pop("average")

        days = d.pop("days")

        high = d.pop("high")

        low = d.pop("low")

        def _parse_today(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        today = _parse_today(d.pop("today"))


        price_range = cls(
            average=average,
            days=days,
            high=high,
            low=low,
            today=today,
        )


        price_range.additional_properties = d
        return price_range

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
