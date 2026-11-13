from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.price_input_condition_type_0 import check_price_input_condition_type_0
from ..models.price_input_condition_type_0 import PriceInputConditionType0
from ..models.price_input_provenance import check_price_input_provenance
from ..models.price_input_provenance import PriceInputProvenance
from ..types import UNSET, Unset
from typing import cast
from uuid import UUID
import datetime






T = TypeVar("T", bound="PriceInput")



@_attrs_define
class PriceInput:
    """ One observed price of an offer whose drive is already known, from a person or a collector
    rechecking it. The offer is named (offer_id), or its drive is (drive_id), with the store,
    seller and condition it is offered in: an offer new to them is made, titled and addressed by
    title and url when given. Nothing here says what a drive is: a drive is made or corrected
    beforehand, and a store page described is taken in at /ingestions.

        Attributes:
            condition (None | PriceInputConditionType0 | Unset):
            drive_id (None | Unset | UUID): Existing drive UUID, for an offer named by its store, seller and condition.
            in_stock (bool | Unset):  Default: True.
            item_price_cents (int | None | Unset): Positive item price in US cents, excluding shipping. Required when in
                stock; when out of stock, omission reuses the previous price.
            notes (str | Unset):  Default: ''.
            observed_at (datetime.datetime | None | Unset): When the price was observed, with a timezone offset. Omit to use
                server time; backdated prices are accepted.
            offer_id (None | Unset | UUID): Existing offer UUID; when supplied, omit drive_id, store, condition, title and
                URL.
            provenance (PriceInputProvenance | Unset): Who submitted the price. A collector submits here only a recheck of
                an offer it names. Default: 'manual'.
            seller (str | Unset):  Default: ''.
            shipping_cents (int | None | Unset): Shipping in US cents: 0 means free, null means unknown. Unknown shipping
                contributes zero to totals. Default: 0.
            store (None | str | Unset): Source key from GET /api/sources, not its UUID. Required with drive_id; other
                requires seller.
            title (None | str | Unset):
            url (None | str | Unset):
     """

    condition: None | PriceInputConditionType0 | Unset = UNSET
    drive_id: None | Unset | UUID = UNSET
    in_stock: bool | Unset = True
    item_price_cents: int | None | Unset = UNSET
    notes: str | Unset = ''
    observed_at: datetime.datetime | None | Unset = UNSET
    offer_id: None | Unset | UUID = UNSET
    provenance: PriceInputProvenance | Unset = 'manual'
    seller: str | Unset = ''
    shipping_cents: int | None | Unset = 0
    store: None | str | Unset = UNSET
    title: None | str | Unset = UNSET
    url: None | str | Unset = UNSET





    def to_dict(self) -> dict[str, Any]:
        condition: None | str | Unset
        if isinstance(self.condition, Unset):
            condition = UNSET
        elif isinstance(self.condition, str):
            condition = self.condition
        else:
            condition = self.condition

        drive_id: None | str | Unset
        if isinstance(self.drive_id, Unset):
            drive_id = UNSET
        elif isinstance(self.drive_id, UUID):
            drive_id = str(self.drive_id)
        else:
            drive_id = self.drive_id

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

        offer_id: None | str | Unset
        if isinstance(self.offer_id, Unset):
            offer_id = UNSET
        elif isinstance(self.offer_id, UUID):
            offer_id = str(self.offer_id)
        else:
            offer_id = self.offer_id

        provenance: str | Unset = UNSET
        if not isinstance(self.provenance, Unset):
            provenance = self.provenance


        seller = self.seller

        shipping_cents: int | None | Unset
        if isinstance(self.shipping_cents, Unset):
            shipping_cents = UNSET
        else:
            shipping_cents = self.shipping_cents

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
        if condition is not UNSET:
            field_dict["condition"] = condition
        if drive_id is not UNSET:
            field_dict["drive_id"] = drive_id
        if in_stock is not UNSET:
            field_dict["in_stock"] = in_stock
        if item_price_cents is not UNSET:
            field_dict["item_price_cents"] = item_price_cents
        if notes is not UNSET:
            field_dict["notes"] = notes
        if observed_at is not UNSET:
            field_dict["observed_at"] = observed_at
        if offer_id is not UNSET:
            field_dict["offer_id"] = offer_id
        if provenance is not UNSET:
            field_dict["provenance"] = provenance
        if seller is not UNSET:
            field_dict["seller"] = seller
        if shipping_cents is not UNSET:
            field_dict["shipping_cents"] = shipping_cents
        if store is not UNSET:
            field_dict["store"] = store
        if title is not UNSET:
            field_dict["title"] = title
        if url is not UNSET:
            field_dict["url"] = url

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
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


        def _parse_drive_id(data: object) -> None | Unset | UUID:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                drive_id_type_0 = UUID(data)



                return drive_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UUID, data)

        drive_id = _parse_drive_id(d.pop("drive_id", UNSET))


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
            condition=condition,
            drive_id=drive_id,
            in_stock=in_stock,
            item_price_cents=item_price_cents,
            notes=notes,
            observed_at=observed_at,
            offer_id=offer_id,
            provenance=provenance,
            seller=seller,
            shipping_cents=shipping_cents,
            store=store,
            title=title,
            url=url,
        )

        return price_input
