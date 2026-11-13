from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset







T = TypeVar("T", bound="TrendPoint")



@_attrs_define
class TrendPoint:
    """ One day of a trend: the median of the drives followed, and the middle half around it.

        Attributes:
            days_ago (int): UTC day offset from the report: 0 is today; points are oldest first.
            high (int):
            low (int):
            median (int):
     """

    days_ago: int
    high: int
    low: int
    median: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        days_ago = self.days_ago

        high = self.high

        low = self.low

        median = self.median


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "days_ago": days_ago,
            "high": high,
            "low": low,
            "median": median,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        days_ago = d.pop("days_ago")

        high = d.pop("high")

        low = d.pop("low")

        median = d.pop("median")

        trend_point = cls(
            days_ago=days_ago,
            high=high,
            low=low,
            median=median,
        )


        trend_point.additional_properties = d
        return trend_point

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
