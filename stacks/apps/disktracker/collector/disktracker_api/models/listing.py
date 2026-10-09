from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.listing_condition import check_listing_condition
from ..models.listing_condition import ListingCondition
from typing import cast
from uuid import UUID
import datetime

if TYPE_CHECKING:
  from ..models.drive import Drive
  from ..models.observation import Observation





T = TypeVar("T", bound="Listing")



@_attrs_define
class Listing:
    """ An offer with every price it has had, oldest first.

        Attributes:
            capacity_gb (int):
            condition (ListingCondition):
            drive (Drive):
            id (UUID):
            last_checked_at (datetime.datetime):
            latest (Observation):
            mpn (str):
            observations (list[Observation]):
            seller (str):
            store (str):
            store_name (str):
            title (str):
            url (None | str):
     """

    capacity_gb: int
    condition: ListingCondition
    drive: Drive
    id: UUID
    last_checked_at: datetime.datetime
    latest: Observation
    mpn: str
    observations: list[Observation]
    seller: str
    store: str
    store_name: str
    title: str
    url: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.drive import Drive # noqa: PLC0415
        from ..models.observation import Observation # noqa: PLC0415
        capacity_gb = self.capacity_gb

        condition: str = self.condition

        drive = self.drive.to_dict()

        id = str(self.id)

        last_checked_at = self.last_checked_at.isoformat()

        latest = self.latest.to_dict()

        mpn = self.mpn

        observations = []
        for observations_item_data in self.observations:
            observations_item = observations_item_data.to_dict()
            observations.append(observations_item)



        seller = self.seller

        store = self.store

        store_name = self.store_name

        title = self.title

        url: None | str
        url = self.url


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "capacity_gb": capacity_gb,
            "condition": condition,
            "drive": drive,
            "id": id,
            "last_checked_at": last_checked_at,
            "latest": latest,
            "mpn": mpn,
            "observations": observations,
            "seller": seller,
            "store": store,
            "store_name": store_name,
            "title": title,
            "url": url,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.drive import Drive # noqa: PLC0415
        from ..models.observation import Observation # noqa: PLC0415
        d = dict(src_dict)
        capacity_gb = d.pop("capacity_gb")

        condition = check_listing_condition(d.pop("condition"))




        drive = Drive.from_dict(d.pop("drive"))




        id = UUID(d.pop("id"))




        last_checked_at = datetime.datetime.fromisoformat(d.pop("last_checked_at"))




        latest = Observation.from_dict(d.pop("latest"))




        mpn = d.pop("mpn")

        observations = []
        _observations = d.pop("observations")
        for observations_item_data in (_observations):
            observations_item = Observation.from_dict(observations_item_data)



            observations.append(observations_item)


        seller = d.pop("seller")

        store = d.pop("store")

        store_name = d.pop("store_name")

        title = d.pop("title")

        def _parse_url(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        url = _parse_url(d.pop("url"))


        listing = cls(
            capacity_gb=capacity_gb,
            condition=condition,
            drive=drive,
            id=id,
            last_checked_at=last_checked_at,
            latest=latest,
            mpn=mpn,
            observations=observations,
            seller=seller,
            store=store,
            store_name=store_name,
            title=title,
            url=url,
        )


        listing.additional_properties = d
        return listing

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
