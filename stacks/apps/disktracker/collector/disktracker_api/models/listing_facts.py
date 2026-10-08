from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.listing_facts_condition_type_0 import check_listing_facts_condition_type_0
from ..models.listing_facts_condition_type_0 import ListingFactsConditionType0
from typing import cast






T = TypeVar("T", bound="ListingFacts")



@_attrs_define
class ListingFacts:
    """ What pasted listing text says of an offer; anything it does not say is null.

        Attributes:
            brand (None | str):
            capacity_gb (int | None):
            condition (ListingFactsConditionType0 | None):
            item_price_cents (int | None):
            mpn (None | str):
            title (None | str):
     """

    brand: None | str
    capacity_gb: int | None
    condition: ListingFactsConditionType0 | None
    item_price_cents: int | None
    mpn: None | str
    title: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        brand: None | str
        brand = self.brand

        capacity_gb: int | None
        capacity_gb = self.capacity_gb

        condition: None | str
        if isinstance(self.condition, str):
            condition = self.condition
        else:
            condition = self.condition

        item_price_cents: int | None
        item_price_cents = self.item_price_cents

        mpn: None | str
        mpn = self.mpn

        title: None | str
        title = self.title


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "brand": brand,
            "capacity_gb": capacity_gb,
            "condition": condition,
            "item_price_cents": item_price_cents,
            "mpn": mpn,
            "title": title,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        def _parse_brand(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        brand = _parse_brand(d.pop("brand"))


        def _parse_capacity_gb(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        capacity_gb = _parse_capacity_gb(d.pop("capacity_gb"))


        def _parse_condition(data: object) -> ListingFactsConditionType0 | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                condition_type_0 = check_listing_facts_condition_type_0(data)



                return condition_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(ListingFactsConditionType0 | None, data)

        condition = _parse_condition(d.pop("condition"))


        def _parse_item_price_cents(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        item_price_cents = _parse_item_price_cents(d.pop("item_price_cents"))


        def _parse_mpn(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        mpn = _parse_mpn(d.pop("mpn"))


        def _parse_title(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        title = _parse_title(d.pop("title"))


        listing_facts = cls(
            brand=brand,
            capacity_gb=capacity_gb,
            condition=condition,
            item_price_cents=item_price_cents,
            mpn=mpn,
            title=title,
        )


        listing_facts.additional_properties = d
        return listing_facts

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
