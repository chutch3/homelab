from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from uuid import UUID






T = TypeVar("T", bound="CombinedOffer")



@_attrs_define
class CombinedOffer:
    """ An offer of the absorbed drive combined into the surviving drive's offer of the same
    store, seller and condition: its prices are that offer's now.

        Attributes:
            absorbed_offer_id (UUID):
            offer_id (UUID):
     """

    absorbed_offer_id: UUID
    offer_id: UUID
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        absorbed_offer_id = str(self.absorbed_offer_id)

        offer_id = str(self.offer_id)


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "absorbed_offer_id": absorbed_offer_id,
            "offer_id": offer_id,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        absorbed_offer_id = UUID(d.pop("absorbed_offer_id"))




        offer_id = UUID(d.pop("offer_id"))




        combined_offer = cls(
            absorbed_offer_id=absorbed_offer_id,
            offer_id=offer_id,
        )


        combined_offer.additional_properties = d
        return combined_offer

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
