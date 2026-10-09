from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast






T = TypeVar("T", bound="PreviewOffer")



@_attrs_define
class PreviewOffer:
    """ One offer as the collector read it from a source being tested; nothing is kept.

        Attributes:
            aliases (list[str]):
            brand (None | str):
            capacity_gb (int | None):
            condition (None | str):
            in_stock (bool):
            item_price_cents (int | None):
            mpn (None | str):
            shipping_cents (int | None):
            title (str):
            url (str):
     """

    aliases: list[str]
    brand: None | str
    capacity_gb: int | None
    condition: None | str
    in_stock: bool
    item_price_cents: int | None
    mpn: None | str
    shipping_cents: int | None
    title: str
    url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        aliases = self.aliases



        brand: None | str
        brand = self.brand

        capacity_gb: int | None
        capacity_gb = self.capacity_gb

        condition: None | str
        condition = self.condition

        in_stock = self.in_stock

        item_price_cents: int | None
        item_price_cents = self.item_price_cents

        mpn: None | str
        mpn = self.mpn

        shipping_cents: int | None
        shipping_cents = self.shipping_cents

        title = self.title

        url = self.url


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "aliases": aliases,
            "brand": brand,
            "capacity_gb": capacity_gb,
            "condition": condition,
            "in_stock": in_stock,
            "item_price_cents": item_price_cents,
            "mpn": mpn,
            "shipping_cents": shipping_cents,
            "title": title,
            "url": url,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        aliases = cast(list[str], d.pop("aliases"))


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


        def _parse_condition(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        condition = _parse_condition(d.pop("condition"))


        in_stock = d.pop("in_stock")

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


        def _parse_shipping_cents(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        shipping_cents = _parse_shipping_cents(d.pop("shipping_cents"))


        title = d.pop("title")

        url = d.pop("url")

        preview_offer = cls(
            aliases=aliases,
            brand=brand,
            capacity_gb=capacity_gb,
            condition=condition,
            in_stock=in_stock,
            item_price_cents=item_price_cents,
            mpn=mpn,
            shipping_cents=shipping_cents,
            title=title,
            url=url,
        )


        preview_offer.additional_properties = d
        return preview_offer

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
