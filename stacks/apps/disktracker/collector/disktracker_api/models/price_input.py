from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.price_input_condition import check_price_input_condition
from ..models.price_input_condition import PriceInputCondition
from ..types import UNSET, Unset
from typing import cast
import datetime






T = TypeVar("T", bound="PriceInput")



@_attrs_define
class PriceInput:
    """ One observed price; the offer is identified by MPN + store + seller + condition.

        Attributes:
            condition (PriceInputCondition):
            mpn (str):
            store (str):
            capacity_gb (int | None | Unset):
            in_stock (bool | Unset):  Default: True.
            item_price_cents (int | None | Unset):
            notes (str | Unset):  Default: ''.
            observed_at (datetime.datetime | None | Unset):
            seller (str | Unset):  Default: ''.
            shipping_cents (int | None | Unset):  Default: 0.
            title (None | str | Unset):
            url (None | str | Unset):
     """

    condition: PriceInputCondition
    mpn: str
    store: str
    capacity_gb: int | None | Unset = UNSET
    in_stock: bool | Unset = True
    item_price_cents: int | None | Unset = UNSET
    notes: str | Unset = ''
    observed_at: datetime.datetime | None | Unset = UNSET
    seller: str | Unset = ''
    shipping_cents: int | None | Unset = 0
    title: None | str | Unset = UNSET
    url: None | str | Unset = UNSET





    def to_dict(self) -> dict[str, Any]:
        condition: str = self.condition

        mpn = self.mpn

        store = self.store

        capacity_gb: int | None | Unset
        if isinstance(self.capacity_gb, Unset):
            capacity_gb = UNSET
        else:
            capacity_gb = self.capacity_gb

        in_stock = self.in_stock

        item_price_cents: int | None | Unset
        if isinstance(self.item_price_cents, Unset):
            item_price_cents = UNSET
        else:
            item_price_cents = self.item_price_cents

        notes = self.notes

        observed_at: None | str | Unset
        if isinstance(self.observed_at, Unset):
            observed_at = UNSET
        elif isinstance(self.observed_at, datetime.datetime):
            observed_at = self.observed_at.isoformat()
        else:
            observed_at = self.observed_at

        seller = self.seller

        shipping_cents: int | None | Unset
        if isinstance(self.shipping_cents, Unset):
            shipping_cents = UNSET
        else:
            shipping_cents = self.shipping_cents

        title: None | str | Unset
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        url: None | str | Unset
        if isinstance(self.url, Unset):
            url = UNSET
        else:
            url = self.url


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "condition": condition,
            "mpn": mpn,
            "store": store,
        })
        if capacity_gb is not UNSET:
            field_dict["capacity_gb"] = capacity_gb
        if in_stock is not UNSET:
            field_dict["in_stock"] = in_stock
        if item_price_cents is not UNSET:
            field_dict["item_price_cents"] = item_price_cents
        if notes is not UNSET:
            field_dict["notes"] = notes
        if observed_at is not UNSET:
            field_dict["observed_at"] = observed_at
        if seller is not UNSET:
            field_dict["seller"] = seller
        if shipping_cents is not UNSET:
            field_dict["shipping_cents"] = shipping_cents
        if title is not UNSET:
            field_dict["title"] = title
        if url is not UNSET:
            field_dict["url"] = url

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        condition = check_price_input_condition(d.pop("condition"))




        mpn = d.pop("mpn")

        store = d.pop("store")

        def _parse_capacity_gb(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        capacity_gb = _parse_capacity_gb(d.pop("capacity_gb", UNSET))


        in_stock = d.pop("in_stock", UNSET)

        def _parse_item_price_cents(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        item_price_cents = _parse_item_price_cents(d.pop("item_price_cents", UNSET))


        notes = d.pop("notes", UNSET)

        def _parse_observed_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                observed_at_type_0 = datetime.datetime.fromisoformat(data)



                return observed_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        observed_at = _parse_observed_at(d.pop("observed_at", UNSET))


        seller = d.pop("seller", UNSET)

        def _parse_shipping_cents(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        shipping_cents = _parse_shipping_cents(d.pop("shipping_cents", UNSET))


        def _parse_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        title = _parse_title(d.pop("title", UNSET))


        def _parse_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        url = _parse_url(d.pop("url", UNSET))


        price_input = cls(
            condition=condition,
            mpn=mpn,
            store=store,
            capacity_gb=capacity_gb,
            in_stock=in_stock,
            item_price_cents=item_price_cents,
            notes=notes,
            observed_at=observed_at,
            seller=seller,
            shipping_cents=shipping_cents,
            title=title,
            url=url,
        )

        return price_input
