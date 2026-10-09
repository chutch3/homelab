from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.specifications import Specifications





T = TypeVar("T", bound="DriveSpecifications")



@_attrs_define
class DriveSpecifications:
    """
        Attributes:
            capacity_gb (int):
            specifications (Specifications):
            brand (None | str | Unset):
     """

    capacity_gb: int
    specifications: Specifications
    brand: None | str | Unset = UNSET





    def to_dict(self) -> dict[str, Any]:
        from ..models.specifications import Specifications # noqa: PLC0415
        capacity_gb = self.capacity_gb

        specifications = self.specifications.to_dict()

        brand: None | str | Unset
        if isinstance(self.brand, Unset):
            brand = UNSET
        else:
            brand = self.brand


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "capacity_gb": capacity_gb,
            "specifications": specifications,
        })
        if brand is not UNSET:
            field_dict["brand"] = brand

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.specifications import Specifications # noqa: PLC0415
        d = dict(src_dict)
        capacity_gb = d.pop("capacity_gb")

        specifications = Specifications.from_dict(d.pop("specifications"))




        def _parse_brand(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        brand = _parse_brand(d.pop("brand", UNSET))


        drive_specifications = cls(
            capacity_gb=capacity_gb,
            specifications=specifications,
            brand=brand,
        )

        return drive_specifications
