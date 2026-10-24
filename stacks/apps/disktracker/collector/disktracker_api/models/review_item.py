from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.review_item_condition_type_0 import check_review_item_condition_type_0
from ..models.review_item_condition_type_0 import ReviewItemConditionType0
from ..models.review_item_provenance import check_review_item_provenance
from ..models.review_item_provenance import ReviewItemProvenance
from ..models.review_item_reason import check_review_item_reason
from ..models.review_item_reason import ReviewItemReason
from typing import cast
from uuid import UUID
import datetime

if TYPE_CHECKING:
  from ..models.drive import Drive
  from ..models.specifications_output import SpecificationsOutput





T = TypeVar("T", bound="ReviewItem")



@_attrs_define
class ReviewItem:
    """ A listing waiting for a reviewer to say what it is: what its page said, as it said it.
    Several offers of one page each wait as their own.

        Attributes:
            aliases (list[str] | None): Other MPNs the page gave; null where they were not kept (queued before now).
            brand (None | str):
            capacity_gb (int | None):
            condition (None | ReviewItemConditionType0): As the page gave it; null where it gave none.
            conflict_drive_id (None | UUID): For alias_conflict: that other drive.
            conflict_mpn (None | str): For alias_conflict: the MPN the page named that another drive goes by.
            drive (Drive | None): The drive its MPN names as recorded now, to set what was collected beside; null when it
                names none.
            first_seen_at (datetime.datetime):
            id (UUID):
            in_stock (bool):
            item_price_cents (int | None):
            last_seen_at (datetime.datetime):
            mpn (None | str): The MPN as the page gave it; null where it gave none.
            provenance (ReviewItemProvenance):
            reason (ReviewItemReason):
            seller (str):
            shipping_cents (int | None):
            specifications (None | SpecificationsOutput): What the page said of the drive; null where nothing was kept.
            store (str):
            title (str):
            url (str):
     """

    aliases: list[str] | None
    brand: None | str
    capacity_gb: int | None
    condition: None | ReviewItemConditionType0
    conflict_drive_id: None | UUID
    conflict_mpn: None | str
    drive: Drive | None
    first_seen_at: datetime.datetime
    id: UUID
    in_stock: bool
    item_price_cents: int | None
    last_seen_at: datetime.datetime
    mpn: None | str
    provenance: ReviewItemProvenance
    reason: ReviewItemReason
    seller: str
    shipping_cents: int | None
    specifications: None | SpecificationsOutput
    store: str
    title: str
    url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.drive import Drive # noqa: PLC0415
        from ..models.specifications_output import SpecificationsOutput # noqa: PLC0415
        aliases: list[str] | None
        if isinstance(self.aliases, list):
            aliases = self.aliases


        else:
            aliases = self.aliases

        brand: None | str
        brand = self.brand

        capacity_gb: int | None
        capacity_gb = self.capacity_gb

        condition: None | str
        if isinstance(self.condition, str):
            condition = self.condition
        else:
            condition = self.condition

        conflict_drive_id: None | str
        if isinstance(self.conflict_drive_id, UUID):
            conflict_drive_id = str(self.conflict_drive_id)
        else:
            conflict_drive_id = self.conflict_drive_id

        conflict_mpn: None | str
        conflict_mpn = self.conflict_mpn

        drive: dict[str, Any] | None
        if isinstance(self.drive, Drive):
            drive = self.drive.to_dict()
        else:
            drive = self.drive

        first_seen_at = self.first_seen_at.isoformat()

        id = str(self.id)

        in_stock = self.in_stock

        item_price_cents: int | None
        item_price_cents = self.item_price_cents

        last_seen_at = self.last_seen_at.isoformat()

        mpn: None | str
        mpn = self.mpn

        provenance: str = self.provenance

        reason: str = self.reason

        seller = self.seller

        shipping_cents: int | None
        shipping_cents = self.shipping_cents

        specifications: dict[str, Any] | None
        if isinstance(self.specifications, SpecificationsOutput):
            specifications = self.specifications.to_dict()
        else:
            specifications = self.specifications

        store = self.store

        title = self.title

        url = self.url


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "aliases": aliases,
            "brand": brand,
            "capacity_gb": capacity_gb,
            "condition": condition,
            "conflict_drive_id": conflict_drive_id,
            "conflict_mpn": conflict_mpn,
            "drive": drive,
            "first_seen_at": first_seen_at,
            "id": id,
            "in_stock": in_stock,
            "item_price_cents": item_price_cents,
            "last_seen_at": last_seen_at,
            "mpn": mpn,
            "provenance": provenance,
            "reason": reason,
            "seller": seller,
            "shipping_cents": shipping_cents,
            "specifications": specifications,
            "store": store,
            "title": title,
            "url": url,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.drive import Drive # noqa: PLC0415
        from ..models.specifications_output import SpecificationsOutput # noqa: PLC0415
        d = dict(src_dict)
        def _parse_aliases(data: object) -> list[str] | None:
            if data is None:
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                aliases_type_0 = cast(list[str], data)

                return aliases_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None, data)

        aliases = _parse_aliases(d.pop("aliases"))


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


        def _parse_condition(data: object) -> None | ReviewItemConditionType0:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                condition_type_0 = check_review_item_condition_type_0(data)



                return condition_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | ReviewItemConditionType0, data)

        condition = _parse_condition(d.pop("condition"))


        def _parse_conflict_drive_id(data: object) -> None | UUID:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                conflict_drive_id_type_0 = UUID(data)



                return conflict_drive_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | UUID, data)

        conflict_drive_id = _parse_conflict_drive_id(d.pop("conflict_drive_id"))


        def _parse_conflict_mpn(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        conflict_mpn = _parse_conflict_mpn(d.pop("conflict_mpn"))


        def _parse_drive(data: object) -> Drive | None:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                drive_type_0 = Drive.from_dict(data)



                return drive_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(Drive | None, data)

        drive = _parse_drive(d.pop("drive"))


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


        provenance = check_review_item_provenance(d.pop("provenance"))




        reason = check_review_item_reason(d.pop("reason"))




        seller = d.pop("seller")

        def _parse_shipping_cents(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        shipping_cents = _parse_shipping_cents(d.pop("shipping_cents"))


        def _parse_specifications(data: object) -> None | SpecificationsOutput:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                specifications_type_0 = SpecificationsOutput.from_dict(data)



                return specifications_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SpecificationsOutput, data)

        specifications = _parse_specifications(d.pop("specifications"))


        store = d.pop("store")

        title = d.pop("title")

        url = d.pop("url")

        review_item = cls(
            aliases=aliases,
            brand=brand,
            capacity_gb=capacity_gb,
            condition=condition,
            conflict_drive_id=conflict_drive_id,
            conflict_mpn=conflict_mpn,
            drive=drive,
            first_seen_at=first_seen_at,
            id=id,
            in_stock=in_stock,
            item_price_cents=item_price_cents,
            last_seen_at=last_seen_at,
            mpn=mpn,
            provenance=provenance,
            reason=reason,
            seller=seller,
            shipping_cents=shipping_cents,
            specifications=specifications,
            store=store,
            title=title,
            url=url,
        )


        review_item.additional_properties = d
        return review_item

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
