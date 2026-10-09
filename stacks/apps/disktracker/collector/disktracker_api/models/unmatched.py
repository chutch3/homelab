from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.unmatched_condition_type_0 import check_unmatched_condition_type_0
from ..models.unmatched_condition_type_0 import UnmatchedConditionType0
from ..models.unmatched_reason import check_unmatched_reason
from ..models.unmatched_reason import UnmatchedReason
from typing import cast
from uuid import UUID
import datetime






T = TypeVar("T", bound="Unmatched")



@_attrs_define
class Unmatched:
    """
        Attributes:
            capacity_gb (int | None):
            condition (None | UnmatchedConditionType0):
            first_seen_at (datetime.datetime):
            id (UUID):
            in_stock (bool):
            item_price_cents (int | None):
            last_seen_at (datetime.datetime):
            mpn (None | str):
            reason (UnmatchedReason):
            seller (str):
            shipping_cents (int | None):
            source (str):
            title (str):
            url (str):
     """

    capacity_gb: int | None
    condition: None | UnmatchedConditionType0
    first_seen_at: datetime.datetime
    id: UUID
    in_stock: bool
    item_price_cents: int | None
    last_seen_at: datetime.datetime
    mpn: None | str
    reason: UnmatchedReason
    seller: str
    shipping_cents: int | None
    source: str
    title: str
    url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        capacity_gb: int | None
        capacity_gb = self.capacity_gb

        condition: None | str
        if isinstance(self.condition, str):
            condition = self.condition
        else:
            condition = self.condition

        first_seen_at = self.first_seen_at.isoformat()

        id = str(self.id)

        in_stock = self.in_stock

        item_price_cents: int | None
        item_price_cents = self.item_price_cents

        last_seen_at = self.last_seen_at.isoformat()

        mpn: None | str
        mpn = self.mpn

        reason: str = self.reason

        seller = self.seller

        shipping_cents: int | None
        shipping_cents = self.shipping_cents

        source = self.source

        title = self.title

        url = self.url


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "capacity_gb": capacity_gb,
            "condition": condition,
            "first_seen_at": first_seen_at,
            "id": id,
            "in_stock": in_stock,
            "item_price_cents": item_price_cents,
            "last_seen_at": last_seen_at,
            "mpn": mpn,
            "reason": reason,
            "seller": seller,
            "shipping_cents": shipping_cents,
            "source": source,
            "title": title,
            "url": url,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        def _parse_capacity_gb(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        capacity_gb = _parse_capacity_gb(d.pop("capacity_gb"))


        def _parse_condition(data: object) -> None | UnmatchedConditionType0:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                condition_type_0 = check_unmatched_condition_type_0(data)



                return condition_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | UnmatchedConditionType0, data)

        condition = _parse_condition(d.pop("condition"))


        first_seen_at = datetime.datetime.fromisoformat(d.pop("first_seen_at"))




        id = UUID(d.pop("id"))




        in_stock = d.pop("in_stock")

        def _parse_item_price_cents(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        item_price_cents = _parse_item_price_cents(d.pop("item_price_cents"))


        last_seen_at = datetime.datetime.fromisoformat(d.pop("last_seen_at"))




        def _parse_mpn(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        mpn = _parse_mpn(d.pop("mpn"))


        reason = check_unmatched_reason(d.pop("reason"))




        seller = d.pop("seller")

        def _parse_shipping_cents(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        shipping_cents = _parse_shipping_cents(d.pop("shipping_cents"))


        source = d.pop("source")

        title = d.pop("title")

        url = d.pop("url")

        unmatched = cls(
            capacity_gb=capacity_gb,
            condition=condition,
            first_seen_at=first_seen_at,
            id=id,
            in_stock=in_stock,
            item_price_cents=item_price_cents,
            last_seen_at=last_seen_at,
            mpn=mpn,
            reason=reason,
            seller=seller,
            shipping_cents=shipping_cents,
            source=source,
            title=title,
            url=url,
        )


        unmatched.additional_properties = d
        return unmatched

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
