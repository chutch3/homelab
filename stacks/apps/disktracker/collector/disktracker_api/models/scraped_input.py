from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.scraped_input_condition_type_0 import check_scraped_input_condition_type_0
from ..models.scraped_input_condition_type_0 import ScrapedInputConditionType0
from ..types import UNSET, Unset
from typing import cast
import datetime

if TYPE_CHECKING:
  from ..models.specifications import Specifications





T = TypeVar("T", bound="ScrapedInput")



@_attrs_define
class ScrapedInput:
    """ An offer as a collector saw it at its source, which is the store it is recorded under;
    MPN or condition may be missing until reviewed.

        Attributes:
            source (str):
            title (str):
            url (str):
            aliases (list[str] | Unset):
            brand (None | str | Unset):
            capacity_gb (int | None | Unset):
            condition (None | ScrapedInputConditionType0 | Unset):
            in_stock (bool | Unset):  Default: True.
            item_price_cents (int | None | Unset):
            mpn (None | str | Unset):
            notes (str | Unset):  Default: ''.
            observed_at (datetime.datetime | None | Unset):
            seller (str | Unset):  Default: ''.
            shipping_cents (int | None | Unset):  Default: 0.
            specifications (None | Specifications | Unset):
     """

    source: str
    title: str
    url: str
    aliases: list[str] | Unset = UNSET
    brand: None | str | Unset = UNSET
    capacity_gb: int | None | Unset = UNSET
    condition: None | ScrapedInputConditionType0 | Unset = UNSET
    in_stock: bool | Unset = True
    item_price_cents: int | None | Unset = UNSET
    mpn: None | str | Unset = UNSET
    notes: str | Unset = ''
    observed_at: datetime.datetime | None | Unset = UNSET
    seller: str | Unset = ''
    shipping_cents: int | None | Unset = 0
    specifications: None | Specifications | Unset = UNSET





    def to_dict(self) -> dict[str, Any]:
        from ..models.specifications import Specifications # noqa: PLC0415
        source = self.source

        title = self.title

        url = self.url

        aliases: list[str] | Unset = UNSET
        if not isinstance(self.aliases, Unset):
            aliases = self.aliases



        brand: None | str | Unset
        if isinstance(self.brand, Unset):
            brand = UNSET
        else:
            brand = self.brand

        capacity_gb: int | None | Unset
        if isinstance(self.capacity_gb, Unset):
            capacity_gb = UNSET
        else:
            capacity_gb = self.capacity_gb

        condition: None | str | Unset
        if isinstance(self.condition, Unset):
            condition = UNSET
        elif isinstance(self.condition, str):
            condition = self.condition
        else:
            condition = self.condition

        in_stock = self.in_stock

        item_price_cents: int | None | Unset
        if isinstance(self.item_price_cents, Unset):
            item_price_cents = UNSET
        else:
            item_price_cents = self.item_price_cents

        mpn: None | str | Unset
        if isinstance(self.mpn, Unset):
            mpn = UNSET
        else:
            mpn = self.mpn

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

        specifications: dict[str, Any] | None | Unset
        if isinstance(self.specifications, Unset):
            specifications = UNSET
        elif isinstance(self.specifications, Specifications):
            specifications = self.specifications.to_dict()
        else:
            specifications = self.specifications


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "source": source,
            "title": title,
            "url": url,
        })
        if aliases is not UNSET:
            field_dict["aliases"] = aliases
        if brand is not UNSET:
            field_dict["brand"] = brand
        if capacity_gb is not UNSET:
            field_dict["capacity_gb"] = capacity_gb
        if condition is not UNSET:
            field_dict["condition"] = condition
        if in_stock is not UNSET:
            field_dict["in_stock"] = in_stock
        if item_price_cents is not UNSET:
            field_dict["item_price_cents"] = item_price_cents
        if mpn is not UNSET:
            field_dict["mpn"] = mpn
        if notes is not UNSET:
            field_dict["notes"] = notes
        if observed_at is not UNSET:
            field_dict["observed_at"] = observed_at
        if seller is not UNSET:
            field_dict["seller"] = seller
        if shipping_cents is not UNSET:
            field_dict["shipping_cents"] = shipping_cents
        if specifications is not UNSET:
            field_dict["specifications"] = specifications

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.specifications import Specifications # noqa: PLC0415
        d = dict(src_dict)
        source = d.pop("source")

        title = d.pop("title")

        url = d.pop("url")

        aliases = cast(list[str], d.pop("aliases", UNSET))


        def _parse_brand(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        brand = _parse_brand(d.pop("brand", UNSET))


        def _parse_capacity_gb(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        capacity_gb = _parse_capacity_gb(d.pop("capacity_gb", UNSET))


        def _parse_condition(data: object) -> None | ScrapedInputConditionType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                condition_type_0 = check_scraped_input_condition_type_0(data)



                return condition_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | ScrapedInputConditionType0 | Unset, data)

        condition = _parse_condition(d.pop("condition", UNSET))


        in_stock = d.pop("in_stock", UNSET)

        def _parse_item_price_cents(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        item_price_cents = _parse_item_price_cents(d.pop("item_price_cents", UNSET))


        def _parse_mpn(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        mpn = _parse_mpn(d.pop("mpn", UNSET))


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


        def _parse_specifications(data: object) -> None | Specifications | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                specifications_type_0 = Specifications.from_dict(data)



                return specifications_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Specifications | Unset, data)

        specifications = _parse_specifications(d.pop("specifications", UNSET))


        scraped_input = cls(
            source=source,
            title=title,
            url=url,
            aliases=aliases,
            brand=brand,
            capacity_gb=capacity_gb,
            condition=condition,
            in_stock=in_stock,
            item_price_cents=item_price_cents,
            mpn=mpn,
            notes=notes,
            observed_at=observed_at,
            seller=seller,
            shipping_cents=shipping_cents,
            specifications=specifications,
        )

        return scraped_input
