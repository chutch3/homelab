from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.drive import Drive
  from ..models.offer_summary import OfferSummary
  from ..models.price_range import PriceRange





T = TypeVar("T", bound="DriveRow")



@_attrs_define
class DriveRow:
    """ A drive as the list shows it: by its cheapest matching offer in stock (else its cheapest
    matching offer), with every offer of it that matches, and the range of its price in the
    representative's condition. key: what the app opens the drive by.

        Attributes:
            drive (Drive):
            key (str):
            offers (list[OfferSummary]):
            range_ (None | PriceRange):
            representative (OfferSummary): An offer with its latest price; what a table of offers needs.
     """

    drive: Drive
    key: str
    offers: list[OfferSummary]
    range_: None | PriceRange
    representative: OfferSummary
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.drive import Drive # noqa: PLC0415
        from ..models.offer_summary import OfferSummary # noqa: PLC0415
        from ..models.price_range import PriceRange # noqa: PLC0415
        drive = self.drive.to_dict()

        key = self.key

        offers = []
        for offers_item_data in self.offers:
            offers_item = offers_item_data.to_dict()
            offers.append(offers_item)



        range_: dict[str, Any] | None
        if isinstance(self.range_, PriceRange):
            range_ = self.range_.to_dict()
        else:
            range_ = self.range_

        representative = self.representative.to_dict()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "drive": drive,
            "key": key,
            "offers": offers,
            "range": range_,
            "representative": representative,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.drive import Drive # noqa: PLC0415
        from ..models.offer_summary import OfferSummary # noqa: PLC0415
        from ..models.price_range import PriceRange # noqa: PLC0415
        d = dict(src_dict)
        drive = Drive.from_dict(d.pop("drive"))




        key = d.pop("key")

        offers = []
        _offers = d.pop("offers")
        for offers_item_data in (_offers):
            offers_item = OfferSummary.from_dict(offers_item_data)



            offers.append(offers_item)


        def _parse_range_(data: object) -> None | PriceRange:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                range_type_0 = PriceRange.from_dict(data)



                return range_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | PriceRange, data)

        range_ = _parse_range_(d.pop("range"))


        representative = OfferSummary.from_dict(d.pop("representative"))




        drive_row = cls(
            drive=drive,
            key=key,
            offers=offers,
            range_=range_,
            representative=representative,
        )


        drive_row.additional_properties = d
        return drive_row

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
