from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.condition_prices_condition import check_condition_prices_condition
from ..models.condition_prices_condition import ConditionPricesCondition
from typing import cast






T = TypeVar("T", bound="ConditionPrices")



@_attrs_define
class ConditionPrices:
    """ A condition a drive is offered in among the offers that match: how many offers, how many
    of them in stock, and the lowest total of those (null when none is).

        Attributes:
            condition (ConditionPricesCondition):
            in_stock (int):
            lowest_total_cents (int | None):
            offers (int):
     """

    condition: ConditionPricesCondition
    in_stock: int
    lowest_total_cents: int | None
    offers: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        condition: str = self.condition

        in_stock = self.in_stock

        lowest_total_cents: int | None
        lowest_total_cents = self.lowest_total_cents

        offers = self.offers


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "condition": condition,
            "in_stock": in_stock,
            "lowest_total_cents": lowest_total_cents,
            "offers": offers,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        condition = check_condition_prices_condition(d.pop("condition"))




        in_stock = d.pop("in_stock")

        def _parse_lowest_total_cents(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        lowest_total_cents = _parse_lowest_total_cents(d.pop("lowest_total_cents"))


        offers = d.pop("offers")

        condition_prices = cls(
            condition=condition,
            in_stock=in_stock,
            lowest_total_cents=lowest_total_cents,
            offers=offers,
        )


        condition_prices.additional_properties = d
        return condition_prices

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
