from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from uuid import UUID
import datetime






T = TypeVar("T", bound="Observation")



@_attrs_define
class Observation:
    """
        Attributes:
            acquisition_method (str):
            entered_at (datetime.datetime):
            id (UUID):
            in_stock (bool):
            item_price_cents (int):
            notes (str):
            observed_at (datetime.datetime):
            price_per_tb (str):
            shipping_cents (int | None):
            shipping_known (bool):
            total_cents (int):
     """

    acquisition_method: str
    entered_at: datetime.datetime
    id: UUID
    in_stock: bool
    item_price_cents: int
    notes: str
    observed_at: datetime.datetime
    price_per_tb: str
    shipping_cents: int | None
    shipping_known: bool
    total_cents: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        acquisition_method = self.acquisition_method

        entered_at = self.entered_at.isoformat()

        id = str(self.id)

        in_stock = self.in_stock

        item_price_cents = self.item_price_cents

        notes = self.notes

        observed_at = self.observed_at.isoformat()

        price_per_tb = self.price_per_tb

        shipping_cents: int | None
        shipping_cents = self.shipping_cents

        shipping_known = self.shipping_known

        total_cents = self.total_cents


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "acquisition_method": acquisition_method,
            "entered_at": entered_at,
            "id": id,
            "in_stock": in_stock,
            "item_price_cents": item_price_cents,
            "notes": notes,
            "observed_at": observed_at,
            "price_per_tb": price_per_tb,
            "shipping_cents": shipping_cents,
            "shipping_known": shipping_known,
            "total_cents": total_cents,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        acquisition_method = d.pop("acquisition_method")

        entered_at = datetime.datetime.fromisoformat(d.pop("entered_at"))




        id = UUID(d.pop("id"))




        in_stock = d.pop("in_stock")

        item_price_cents = d.pop("item_price_cents")

        notes = d.pop("notes")

        observed_at = datetime.datetime.fromisoformat(d.pop("observed_at"))




        price_per_tb = d.pop("price_per_tb")

        def _parse_shipping_cents(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        shipping_cents = _parse_shipping_cents(d.pop("shipping_cents"))


        shipping_known = d.pop("shipping_known")

        total_cents = d.pop("total_cents")

        observation = cls(
            acquisition_method=acquisition_method,
            entered_at=entered_at,
            id=id,
            in_stock=in_stock,
            item_price_cents=item_price_cents,
            notes=notes,
            observed_at=observed_at,
            price_per_tb=price_per_tb,
            shipping_cents=shipping_cents,
            shipping_known=shipping_known,
            total_cents=total_cents,
        )


        observation.additional_properties = d
        return observation

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
