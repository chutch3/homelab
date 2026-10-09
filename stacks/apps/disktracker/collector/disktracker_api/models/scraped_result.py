from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.scraped_result_status import check_scraped_result_status
from ..models.scraped_result_status import ScrapedResultStatus
from ..types import UNSET, Unset
from typing import cast
from uuid import UUID






T = TypeVar("T", bound="ScrapedResult")



@_attrs_define
class ScrapedResult:
    """
        Attributes:
            status (ScrapedResultStatus):
            listing_id (None | Unset | UUID):
            unmatched_id (None | Unset | UUID):
     """

    status: ScrapedResultStatus
    listing_id: None | Unset | UUID = UNSET
    unmatched_id: None | Unset | UUID = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        status: str = self.status

        listing_id: None | str | Unset
        if isinstance(self.listing_id, Unset):
            listing_id = UNSET
        elif isinstance(self.listing_id, UUID):
            listing_id = str(self.listing_id)
        else:
            listing_id = self.listing_id

        unmatched_id: None | str | Unset
        if isinstance(self.unmatched_id, Unset):
            unmatched_id = UNSET
        elif isinstance(self.unmatched_id, UUID):
            unmatched_id = str(self.unmatched_id)
        else:
            unmatched_id = self.unmatched_id


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "status": status,
        })
        if listing_id is not UNSET:
            field_dict["listing_id"] = listing_id
        if unmatched_id is not UNSET:
            field_dict["unmatched_id"] = unmatched_id

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        status = check_scraped_result_status(d.pop("status"))




        def _parse_listing_id(data: object) -> None | Unset | UUID:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                listing_id_type_0 = UUID(data)



                return listing_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UUID, data)

        listing_id = _parse_listing_id(d.pop("listing_id", UNSET))


        def _parse_unmatched_id(data: object) -> None | Unset | UUID:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                unmatched_id_type_0 = UUID(data)



                return unmatched_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UUID, data)

        unmatched_id = _parse_unmatched_id(d.pop("unmatched_id", UNSET))


        scraped_result = cls(
            status=status,
            listing_id=listing_id,
            unmatched_id=unmatched_id,
        )


        scraped_result.additional_properties = d
        return scraped_result

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
