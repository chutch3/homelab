from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.price_input_condition_type_0 import check_price_input_condition_type_0
from ..models.price_input_condition_type_0 import PriceInputConditionType0
from ..models.price_input_on_unmatched import check_price_input_on_unmatched
from ..models.price_input_on_unmatched import PriceInputOnUnmatched
from ..models.price_input_provenance import check_price_input_provenance
from ..models.price_input_provenance import PriceInputProvenance
from ..types import UNSET, Unset
from typing import cast
from uuid import UUID
import datetime

if TYPE_CHECKING:
  from ..models.specifications_input import SpecificationsInput





T = TypeVar("T", bound="PriceInput")



@_attrs_define
class PriceInput:
    """ One observed price, from a person or a collector alike. The offer it is for is either
    named (offer_id) or described: its store, MPN, condition and, for a one-off store, seller.

    on_unmatched says what to do with a described offer that cannot be matched to a drive (its
    MPN or condition is unknown, its drive's capacity is unknown, or its capacity disagrees with
    the drive's): reject refuses the price; queue keeps it for review, which needs the page and
    title a reviewer is shown.

        Attributes:
            aliases (list[str] | Unset):
            brand (None | str | Unset):
            capacity_gb (int | None | Unset):
            condition (None | PriceInputConditionType0 | Unset):
            in_stock (bool | Unset):  Default: True.
            item_price_cents (int | None | Unset): Positive item price in US cents, excluding shipping. Required when in
                stock; when out of stock, omission reuses the previous price.
            mpn (None | str | Unset):
            notes (str | Unset):  Default: ''.
            observed_at (datetime.datetime | None | Unset): When the price was observed, with a timezone offset. Omit to use
                server time; backdated prices are accepted.
            offer_id (None | Unset | UUID): Existing offer UUID; when supplied, omit store, MPN and condition.
            on_unmatched (PriceInputOnUnmatched | Unset): Reject unmatched input with a field error, or queue it for review.
                Queue requires title and URL. Default: 'reject'.
            provenance (PriceInputProvenance | Unset): Who submitted the price; the offer store identifies where it was
                seen. Default: 'manual'.
            seller (str | Unset):  Default: ''.
            shipping_cents (int | None | Unset): Shipping in US cents: 0 means free, null means unknown. Unknown shipping
                contributes zero to totals. Default: 0.
            specifications (None | SpecificationsInput | Unset):
            store (None | str | Unset): Source key from GET /api/sources, not its UUID. Required unless offer_id is given;
                other requires seller.
            title (None | str | Unset):
            url (None | str | Unset):
     """

    aliases: list[str] | Unset = UNSET
    brand: None | str | Unset = UNSET
    capacity_gb: int | None | Unset = UNSET
    condition: None | PriceInputConditionType0 | Unset = UNSET
    in_stock: bool | Unset = True
    item_price_cents: int | None | Unset = UNSET
    mpn: None | str | Unset = UNSET
    notes: str | Unset = ''
    observed_at: datetime.datetime | None | Unset = UNSET
    offer_id: None | Unset | UUID = UNSET
    on_unmatched: PriceInputOnUnmatched | Unset = 'reject'
    provenance: PriceInputProvenance | Unset = 'manual'
    seller: str | Unset = ''
    shipping_cents: int | None | Unset = 0
    specifications: None | SpecificationsInput | Unset = UNSET
    store: None | str | Unset = UNSET
    title: None | str | Unset = UNSET
    url: None | str | Unset = UNSET





    def to_dict(self) -> dict[str, Any]:
        from ..models.specifications_input import SpecificationsInput # noqa: PLC0415
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

        offer_id: None | str | Unset
        if isinstance(self.offer_id, Unset):
            offer_id = UNSET
        elif isinstance(self.offer_id, UUID):
            offer_id = str(self.offer_id)
        else:
            offer_id = self.offer_id

        on_unmatched: str | Unset = UNSET
        if not isinstance(self.on_unmatched, Unset):
            on_unmatched = self.on_unmatched


        provenance: str | Unset = UNSET
        if not isinstance(self.provenance, Unset):
            provenance = self.provenance


        seller = self.seller

        shipping_cents: int | None | Unset
        if isinstance(self.shipping_cents, Unset):
            shipping_cents = UNSET
        else:
            shipping_cents = self.shipping_cents

        specifications: dict[str, Any] | None | Unset
        if isinstance(self.specifications, Unset):
            specifications = UNSET
        elif isinstance(self.specifications, SpecificationsInput):
            specifications = self.specifications.to_dict()
        else:
            specifications = self.specifications

        store: None | str | Unset
        if isinstance(self.store, Unset):
            store = UNSET
        else:
            store = self.store

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
        if offer_id is not UNSET:
            field_dict["offer_id"] = offer_id
        if on_unmatched is not UNSET:
            field_dict["on_unmatched"] = on_unmatched
        if provenance is not UNSET:
            field_dict["provenance"] = provenance
        if seller is not UNSET:
            field_dict["seller"] = seller
        if shipping_cents is not UNSET:
            field_dict["shipping_cents"] = shipping_cents
        if specifications is not UNSET:
            field_dict["specifications"] = specifications
        if store is not UNSET:
            field_dict["store"] = store
        if title is not UNSET:
            field_dict["title"] = title
        if url is not UNSET:
            field_dict["url"] = url

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.specifications_input import SpecificationsInput # noqa: PLC0415
        d = dict(src_dict)
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


        def _parse_condition(data: object) -> None | PriceInputConditionType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                condition_type_0 = check_price_input_condition_type_0(data)



                return condition_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | PriceInputConditionType0 | Unset, data)

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


        def _parse_offer_id(data: object) -> None | Unset | UUID:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                offer_id_type_0 = UUID(data)



                return offer_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UUID, data)

        offer_id = _parse_offer_id(d.pop("offer_id", UNSET))


        _on_unmatched = d.pop("on_unmatched", UNSET)
        on_unmatched: PriceInputOnUnmatched | Unset
        if isinstance(_on_unmatched,  Unset):
            on_unmatched = UNSET
        else:
            on_unmatched = check_price_input_on_unmatched(_on_unmatched)




        _provenance = d.pop("provenance", UNSET)
        provenance: PriceInputProvenance | Unset
        if isinstance(_provenance,  Unset):
            provenance = UNSET
        else:
            provenance = check_price_input_provenance(_provenance)




        seller = d.pop("seller", UNSET)

        def _parse_shipping_cents(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        shipping_cents = _parse_shipping_cents(d.pop("shipping_cents", UNSET))


        def _parse_specifications(data: object) -> None | SpecificationsInput | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                specifications_type_0 = SpecificationsInput.from_dict(data)



                return specifications_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SpecificationsInput | Unset, data)

        specifications = _parse_specifications(d.pop("specifications", UNSET))


        def _parse_store(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        store = _parse_store(d.pop("store", UNSET))


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
            aliases=aliases,
            brand=brand,
            capacity_gb=capacity_gb,
            condition=condition,
            in_stock=in_stock,
            item_price_cents=item_price_cents,
            mpn=mpn,
            notes=notes,
            observed_at=observed_at,
            offer_id=offer_id,
            on_unmatched=on_unmatched,
            provenance=provenance,
            seller=seller,
            shipping_cents=shipping_cents,
            specifications=specifications,
            store=store,
            title=title,
            url=url,
        )

        return price_input
