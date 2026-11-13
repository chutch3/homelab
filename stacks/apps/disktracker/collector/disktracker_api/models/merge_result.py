from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from typing import Literal, cast
from uuid import UUID

if TYPE_CHECKING:
  from ..models.combined_offer import CombinedOffer





T = TypeVar("T", bound="MergeResult")



@_attrs_define
class MergeResult:
    """
        Attributes:
            absorbed_drive_id (UUID):
            combined_offers (list[CombinedOffer]):
            drive_id (UUID):
            status (Literal['merged']):
     """

    absorbed_drive_id: UUID
    combined_offers: list[CombinedOffer]
    drive_id: UUID
    status: Literal['merged']
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.combined_offer import CombinedOffer # noqa: PLC0415
        absorbed_drive_id = str(self.absorbed_drive_id)

        combined_offers = []
        for combined_offers_item_data in self.combined_offers:
            combined_offers_item = combined_offers_item_data.to_dict()
            combined_offers.append(combined_offers_item)



        drive_id = str(self.drive_id)

        status = self.status


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "absorbed_drive_id": absorbed_drive_id,
            "combined_offers": combined_offers,
            "drive_id": drive_id,
            "status": status,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.combined_offer import CombinedOffer # noqa: PLC0415
        d = dict(src_dict)
        absorbed_drive_id = UUID(d.pop("absorbed_drive_id"))




        combined_offers = []
        _combined_offers = d.pop("combined_offers")
        for combined_offers_item_data in (_combined_offers):
            combined_offers_item = CombinedOffer.from_dict(combined_offers_item_data)



            combined_offers.append(combined_offers_item)


        drive_id = UUID(d.pop("drive_id"))




        status = cast(Literal['merged'] , d.pop("status"))
        if status != 'merged':
            raise ValueError(f"status must match const 'merged', got '{status}'")

        merge_result = cls(
            absorbed_drive_id=absorbed_drive_id,
            combined_offers=combined_offers,
            drive_id=drive_id,
            status=status,
        )


        merge_result.additional_properties = d
        return merge_result

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
