from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.drive import Drive
  from ..models.drive_detail_ranges import DriveDetailRanges
  from ..models.offer_summary import OfferSummary





T = TypeVar("T", bound="DriveDetail")



@_attrs_define
class DriveDetail:
    """ A drive with every offer of it, in every condition, and in each condition it is offered
    in, the range of its lowest item price over the days asked for (null when no offer of it was
    in stock then).

        Attributes:
            drive (Drive):
            offers (list[OfferSummary]):
            ranges (DriveDetailRanges):
     """

    drive: Drive
    offers: list[OfferSummary]
    ranges: DriveDetailRanges
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.drive import Drive # noqa: PLC0415
        from ..models.drive_detail_ranges import DriveDetailRanges # noqa: PLC0415
        from ..models.offer_summary import OfferSummary # noqa: PLC0415
        drive = self.drive.to_dict()

        offers = []
        for offers_item_data in self.offers:
            offers_item = offers_item_data.to_dict()
            offers.append(offers_item)



        ranges = self.ranges.to_dict()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "drive": drive,
            "offers": offers,
            "ranges": ranges,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.drive import Drive # noqa: PLC0415
        from ..models.drive_detail_ranges import DriveDetailRanges # noqa: PLC0415
        from ..models.offer_summary import OfferSummary # noqa: PLC0415
        d = dict(src_dict)
        drive = Drive.from_dict(d.pop("drive"))




        offers = []
        _offers = d.pop("offers")
        for offers_item_data in (_offers):
            offers_item = OfferSummary.from_dict(offers_item_data)



            offers.append(offers_item)


        ranges = DriveDetailRanges.from_dict(d.pop("ranges"))




        drive_detail = cls(
            drive=drive,
            offers=offers,
            ranges=ranges,
        )


        drive_detail.additional_properties = d
        return drive_detail

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
