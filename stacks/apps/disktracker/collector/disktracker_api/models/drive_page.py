from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
import datetime

if TYPE_CHECKING:
  from ..models.drive_row import DriveRow
  from ..models.filter_options import FilterOptions
  from ..models.lowest import Lowest





T = TypeVar("T", bound="DrivePage")



@_attrs_define
class DrivePage:
    """ A part of the drive list. total: drives that match; offers: offers that match; sold_out:
    drives left out only because no store has them in stock. as_of: the moment recency and
    ranges are judged against.

        Attributes:
            as_of (datetime.datetime):
            filter_options (FilterOptions): What the filters can choose from: every option the catalogue has, each with how
                many drives
                choosing it would give, with the search and every other filter as asked but not its own
                group's, whichever page is shown.
            items (list[DriveRow]):
            limit (int):
            lowest (Lowest): The offers with the lowest total and the lowest total per terabyte among every offer that
                matches, in stock and checked recently.
            offers (int):
            offset (int):
            sold_out (int):
            total (int):
     """

    as_of: datetime.datetime
    filter_options: FilterOptions
    items: list[DriveRow]
    limit: int
    lowest: Lowest
    offers: int
    offset: int
    sold_out: int
    total: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.drive_row import DriveRow # noqa: PLC0415
        from ..models.filter_options import FilterOptions # noqa: PLC0415
        from ..models.lowest import Lowest # noqa: PLC0415
        as_of = self.as_of.isoformat()

        filter_options = self.filter_options.to_dict()

        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)



        limit = self.limit

        lowest = self.lowest.to_dict()

        offers = self.offers

        offset = self.offset

        sold_out = self.sold_out

        total = self.total


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "as_of": as_of,
            "filter_options": filter_options,
            "items": items,
            "limit": limit,
            "lowest": lowest,
            "offers": offers,
            "offset": offset,
            "sold_out": sold_out,
            "total": total,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.drive_row import DriveRow # noqa: PLC0415
        from ..models.filter_options import FilterOptions # noqa: PLC0415
        from ..models.lowest import Lowest # noqa: PLC0415
        d = dict(src_dict)
        as_of = datetime.datetime.fromisoformat(d.pop("as_of"))




        filter_options = FilterOptions.from_dict(d.pop("filter_options"))




        items = []
        _items = d.pop("items")
        for items_item_data in (_items):
            items_item = DriveRow.from_dict(items_item_data)



            items.append(items_item)


        limit = d.pop("limit")

        lowest = Lowest.from_dict(d.pop("lowest"))




        offers = d.pop("offers")

        offset = d.pop("offset")

        sold_out = d.pop("sold_out")

        total = d.pop("total")

        drive_page = cls(
            as_of=as_of,
            filter_options=filter_options,
            items=items,
            limit=limit,
            lowest=lowest,
            offers=offers,
            offset=offset,
            sold_out=sold_out,
            total=total,
        )


        drive_page.additional_properties = d
        return drive_page

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
