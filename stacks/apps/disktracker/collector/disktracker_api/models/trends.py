from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.trends_by_type_0 import check_trends_by_type_0
from ..models.trends_by_type_0 import TrendsByType0
from typing import cast
import datetime

if TYPE_CHECKING:
  from ..models.trend_part import TrendPart
  from ..models.trend_series import TrendSeries





T = TypeVar("T", bound="Trends")



@_attrs_define
class Trends:
    """ Item prices over a period, in cents per terabyte. Split by store, each part is instead
    hundredths of a percent above the typical price of the drives that store shares with another.

        Attributes:
            by (None | TrendsByType0):
            days (int):
            market (TrendSeries):
            parts (list[TrendPart]):
            since (datetime.datetime | None): When the first price was seen, whatever the period; null when none was. A
                period opening before it follows no drive.
     """

    by: None | TrendsByType0
    days: int
    market: TrendSeries
    parts: list[TrendPart]
    since: datetime.datetime | None
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.trend_part import TrendPart # noqa: PLC0415
        from ..models.trend_series import TrendSeries # noqa: PLC0415
        by: None | str
        if isinstance(self.by, str):
            by = self.by
        else:
            by = self.by

        days = self.days

        market = self.market.to_dict()

        parts = []
        for parts_item_data in self.parts:
            parts_item = parts_item_data.to_dict()
            parts.append(parts_item)



        since: None | str
        if isinstance(self.since, datetime.datetime):
            since = self.since.isoformat()
        else:
            since = self.since


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "by": by,
            "days": days,
            "market": market,
            "parts": parts,
            "since": since,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.trend_part import TrendPart # noqa: PLC0415
        from ..models.trend_series import TrendSeries # noqa: PLC0415
        d = dict(src_dict)
        def _parse_by(data: object) -> None | TrendsByType0:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                by_type_0 = check_trends_by_type_0(data)



                return by_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | TrendsByType0, data)

        by = _parse_by(d.pop("by"))


        days = d.pop("days")

        market = TrendSeries.from_dict(d.pop("market"))




        parts = []
        _parts = d.pop("parts")
        for parts_item_data in (_parts):
            parts_item = TrendPart.from_dict(parts_item_data)



            parts.append(parts_item)


        def _parse_since(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                since_type_0 = datetime.datetime.fromisoformat(data)



                return since_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        since = _parse_since(d.pop("since"))


        trends = cls(
            by=by,
            days=days,
            market=market,
            parts=parts,
            since=since,
        )


        trends.additional_properties = d
        return trends

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
