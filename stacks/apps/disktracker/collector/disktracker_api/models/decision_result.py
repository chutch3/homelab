from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.decision_result_status import check_decision_result_status
from ..models.decision_result_status import DecisionResultStatus
from typing import cast
from uuid import UUID






T = TypeVar("T", bound="DecisionResult")



@_attrs_define
class DecisionResult:
    """ What a review decision did: matched names the offer its price was recorded for; ignored
    names none.

        Attributes:
            offer_id (None | UUID):
            status (DecisionResultStatus):
     """

    offer_id: None | UUID
    status: DecisionResultStatus
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        offer_id: None | str
        if isinstance(self.offer_id, UUID):
            offer_id = str(self.offer_id)
        else:
            offer_id = self.offer_id

        status: str = self.status


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "offer_id": offer_id,
            "status": status,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        def _parse_offer_id(data: object) -> None | UUID:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                offer_id_type_0 = UUID(data)



                return offer_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | UUID, data)

        offer_id = _parse_offer_id(d.pop("offer_id"))


        status = check_decision_result_status(d.pop("status"))




        decision_result = cls(
            offer_id=offer_id,
            status=status,
        )


        decision_result.additional_properties = d
        return decision_result

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
