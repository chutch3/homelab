from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from uuid import UUID

if TYPE_CHECKING:
  from ..models.specifications import Specifications





T = TypeVar("T", bound="Drive")



@_attrs_define
class Drive:
    """
        Attributes:
            aliases (list[str]):
            brand (None | str):
            capacity_gb (int):
            id (UUID):
            mpn (str):
            specifications (Specifications):
     """

    aliases: list[str]
    brand: None | str
    capacity_gb: int
    id: UUID
    mpn: str
    specifications: Specifications
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.specifications import Specifications # noqa: PLC0415
        aliases = self.aliases



        brand: None | str
        brand = self.brand

        capacity_gb = self.capacity_gb

        id = str(self.id)

        mpn = self.mpn

        specifications = self.specifications.to_dict()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "aliases": aliases,
            "brand": brand,
            "capacity_gb": capacity_gb,
            "id": id,
            "mpn": mpn,
            "specifications": specifications,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.specifications import Specifications # noqa: PLC0415
        d = dict(src_dict)
        aliases = cast(list[str], d.pop("aliases"))


        def _parse_brand(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        brand = _parse_brand(d.pop("brand"))


        capacity_gb = d.pop("capacity_gb")

        id = UUID(d.pop("id"))




        mpn = d.pop("mpn")

        specifications = Specifications.from_dict(d.pop("specifications"))




        drive = cls(
            aliases=aliases,
            brand=brand,
            capacity_gb=capacity_gb,
            id=id,
            mpn=mpn,
            specifications=specifications,
        )


        drive.additional_properties = d
        return drive

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
