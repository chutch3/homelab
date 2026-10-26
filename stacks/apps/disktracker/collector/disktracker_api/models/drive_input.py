from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.specifications_input import SpecificationsInput





T = TypeVar("T", bound="DriveInput")



@_attrs_define
class DriveInput:
    """ A drive made on its own, before any price of it: its MPN, which no drive may go by already,
    its capacity, and what is known of it. Specifications left out are unknown.

        Attributes:
            capacity_gb (int): Capacity in decimal GB; 1 TB = 1,000 GB.
            mpn (str):
            brand (None | str | Unset):
            specifications (SpecificationsInput | Unset):
     """

    capacity_gb: int
    mpn: str
    brand: None | str | Unset = UNSET
    specifications: SpecificationsInput | Unset = UNSET





    def to_dict(self) -> dict[str, Any]:
        from ..models.specifications_input import SpecificationsInput # noqa: PLC0415
        capacity_gb = self.capacity_gb

        mpn = self.mpn

        brand: None | str | Unset
        if isinstance(self.brand, Unset):
            brand = UNSET
        else:
            brand = self.brand

        specifications: dict[str, Any] | Unset = UNSET
        if not isinstance(self.specifications, Unset):
            specifications = self.specifications.to_dict()


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "capacity_gb": capacity_gb,
            "mpn": mpn,
        })
        if brand is not UNSET:
            field_dict["brand"] = brand
        if specifications is not UNSET:
            field_dict["specifications"] = specifications

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.specifications_input import SpecificationsInput # noqa: PLC0415
        d = dict(src_dict)
        capacity_gb = d.pop("capacity_gb")

        mpn = d.pop("mpn")

        def _parse_brand(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        brand = _parse_brand(d.pop("brand", UNSET))


        _specifications = d.pop("specifications", UNSET)
        specifications: SpecificationsInput | Unset
        if isinstance(_specifications,  Unset):
            specifications = UNSET
        else:
            specifications = SpecificationsInput.from_dict(_specifications)




        drive_input = cls(
            capacity_gb=capacity_gb,
            mpn=mpn,
            brand=brand,
            specifications=specifications,
        )

        return drive_input
