from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.price_result_status import check_price_result_status
from ..models.price_result_status import PriceResultStatus
from typing import cast
from uuid import UUID






T = TypeVar("T", bound="PriceResult")



@_attrs_define
class PriceResult:
    """ What was done with a submitted price.

    recorded: offer_id is the offer it is for, and price_id the price made, or null when the
    price was the same as the offer's last and so only counted as a check of it.
    queued: the offer could not be matched and waits for review as review_item_id.
    ignored: nothing was kept, as an earlier review decided, or as it was sold out and never
    seen in stock. Whatever is not named for a status is null.

        Attributes:
            offer_id (None | UUID):
            price_id (None | UUID):
            review_item_id (None | UUID):
            status (PriceResultStatus):
     """

    offer_id: None | UUID
    price_id: None | UUID
    review_item_id: None | UUID
    status: PriceResultStatus
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        offer_id: None | str
        if isinstance(self.offer_id, UUID):
            offer_id = str(self.offer_id)
        else:
            offer_id = self.offer_id

        price_id: None | str
        if isinstance(self.price_id, UUID):
            price_id = str(self.price_id)
        else:
            price_id = self.price_id

        review_item_id: None | str
        if isinstance(self.review_item_id, UUID):
            review_item_id = str(self.review_item_id)
        else:
            review_item_id = self.review_item_id

        status: str = self.status


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "offer_id": offer_id,
            "price_id": price_id,
            "review_item_id": review_item_id,
            "status": status,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        def _parse_offer_id(data: object) -> None | UUID:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                offer_id_type_0 = UUID(data)



                return offer_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | UUID, data)

        offer_id = _parse_offer_id(d.pop("offer_id"))


        def _parse_price_id(data: object) -> None | UUID:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                price_id_type_0 = UUID(data)



                return price_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | UUID, data)

        price_id = _parse_price_id(d.pop("price_id"))


        def _parse_review_item_id(data: object) -> None | UUID:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                review_item_id_type_0 = UUID(data)



                return review_item_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | UUID, data)

        review_item_id = _parse_review_item_id(d.pop("review_item_id"))


        status = check_price_result_status(d.pop("status"))




        price_result = cls(
            offer_id=offer_id,
            price_id=price_id,
            review_item_id=review_item_id,
            status=status,
        )


        price_result.additional_properties = d
        return price_result

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
