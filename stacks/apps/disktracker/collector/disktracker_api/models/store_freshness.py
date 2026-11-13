from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
import datetime






T = TypeVar("T", bound="StoreFreshness")



@_attrs_define
class StoreFreshness:
    """ How fresh a store's prices are: how many offers it has, held ones and all, when the latest
    of them was checked, and when the middle one was (between the middle two, of an even
    number).

        Attributes:
            latest_checked_at (datetime.datetime):
            median_checked_at (datetime.datetime):
            offers (int):
            store (str):
     """

    latest_checked_at: datetime.datetime
    median_checked_at: datetime.datetime
    offers: int
    store: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        latest_checked_at = self.latest_checked_at.isoformat()

        median_checked_at = self.median_checked_at.isoformat()

        offers = self.offers

        store = self.store


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "latest_checked_at": latest_checked_at,
            "median_checked_at": median_checked_at,
            "offers": offers,
            "store": store,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        latest_checked_at = datetime.datetime.fromisoformat(d.pop("latest_checked_at"))




        median_checked_at = datetime.datetime.fromisoformat(d.pop("median_checked_at"))




        offers = d.pop("offers")

        store = d.pop("store")

        store_freshness = cls(
            latest_checked_at=latest_checked_at,
            median_checked_at=median_checked_at,
            offers=offers,
            store=store,
        )


        store_freshness.additional_properties = d
        return store_freshness

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
