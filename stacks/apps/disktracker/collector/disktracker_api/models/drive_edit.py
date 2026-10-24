from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.specifications_edit import SpecificationsEdit





T = TypeVar("T", bound="DriveEdit")



@_attrs_define
class DriveEdit:
    """ A drive corrected by hand: what is given changes, and what is left out stays. Capacity and
    specifications cannot be cleared; a null or blank brand makes it unknown again, until a source
    names it. Its MPNs change only by declaring an alias.

        Attributes:
            brand (None | str | Unset):
            capacity_gb (int | Unset): Capacity in decimal GB; 1 TB = 1,000 GB.
            specifications (SpecificationsEdit | Unset): Specifications corrected by hand: each one given takes the place of
                the one kept, and
                each one left out stays. None can be cleared; unknown is a value like any other.
     """

    brand: None | str | Unset = UNSET
    capacity_gb: int | Unset = UNSET
    specifications: SpecificationsEdit | Unset = UNSET





    def to_dict(self) -> dict[str, Any]:
        from ..models.specifications_edit import SpecificationsEdit # noqa: PLC0415
        brand: None | str | Unset
        if isinstance(self.brand, Unset):
            brand = UNSET
        else:
            brand = self.brand

        capacity_gb = self.capacity_gb

        specifications: dict[str, Any] | Unset = UNSET
        if not isinstance(self.specifications, Unset):
            specifications = self.specifications.to_dict()


        field_dict: dict[str, Any] = {}

        field_dict.update({
        })
        if brand is not UNSET:
            field_dict["brand"] = brand
        if capacity_gb is not UNSET:
            field_dict["capacity_gb"] = capacity_gb
        if specifications is not UNSET:
            field_dict["specifications"] = specifications

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.specifications_edit import SpecificationsEdit # noqa: PLC0415
        d = dict(src_dict)
        def _parse_brand(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        brand = _parse_brand(d.pop("brand", UNSET))


        capacity_gb = d.pop("capacity_gb", UNSET)

        _specifications = d.pop("specifications", UNSET)
        specifications: SpecificationsEdit | Unset
        if isinstance(_specifications,  Unset):
            specifications = UNSET
        else:
            specifications = SpecificationsEdit.from_dict(_specifications)




        drive_edit = cls(
            brand=brand,
            capacity_gb=capacity_gb,
            specifications=specifications,
        )

        return drive_edit
