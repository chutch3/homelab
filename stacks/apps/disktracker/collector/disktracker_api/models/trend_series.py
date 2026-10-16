from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.trend_point import TrendPoint





T = TypeVar("T", bound="TrendSeries")



@_attrs_define
class TrendSeries:
    """
        Attributes:
            counted (int): Number of drives followed: only those priced at the period opening.
            of (int): Number of drives with prices in the period, including later arrivals.
            points (list[TrendPoint]):
     """

    counted: int
    of: int
    points: list[TrendPoint]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.trend_point import TrendPoint # noqa: PLC0415
        counted = self.counted

        of = self.of

        points = []
        for points_item_data in self.points:
            points_item = points_item_data.to_dict()
            points.append(points_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "counted": counted,
            "of": of,
            "points": points,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.trend_point import TrendPoint # noqa: PLC0415
        d = dict(src_dict)
        counted = d.pop("counted")

        of = d.pop("of")

        points = []
        _points = d.pop("points")
        for points_item_data in (_points):
            points_item = TrendPoint.from_dict(points_item_data)



            points.append(points_item)


        trend_series = cls(
            counted=counted,
            of=of,
            points=points,
        )


        trend_series.additional_properties = d
        return trend_series

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
