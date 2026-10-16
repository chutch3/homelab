from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.price_range import PriceRange





T = TypeVar("T", bound="DriveDetailRanges")



@_attrs_define
class DriveDetailRanges:


    additional_properties: dict[str, None | PriceRange] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.price_range import PriceRange # noqa: PLC0415

        field_dict: dict[str, Any] = {}
        for prop_name, prop in self.additional_properties.items():

            if isinstance(prop, PriceRange):
                field_dict[prop_name] = prop.to_dict()
            else:
                field_dict[prop_name] = prop


        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.price_range import PriceRange # noqa: PLC0415
        d = dict(src_dict)
        drive_detail_ranges = cls(
        )


        additional_properties = {}
        for prop_name, prop_dict in d.items():
            def _parse_additional_property(data: object) -> None | PriceRange:
                if data is None:
                    return data
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    additional_property_type_0 = PriceRange.from_dict(data)



                    return additional_property_type_0
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                return cast(None | PriceRange, data)

            additional_property = _parse_additional_property(prop_dict)

            additional_properties[prop_name] = additional_property

        drive_detail_ranges.additional_properties = additional_properties
        return drive_detail_ranges

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> None | PriceRange:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: None | PriceRange) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
