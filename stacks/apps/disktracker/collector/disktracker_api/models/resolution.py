from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.resolution_condition import check_resolution_condition
from ..models.resolution_condition import ResolutionCondition
from ..types import UNSET, Unset
from typing import cast






T = TypeVar("T", bound="Resolution")



@_attrs_define
class Resolution:
    """ What a reviewer decided a queued scraped offer is.

        Attributes:
            condition (ResolutionCondition):
            mpn (str):
            capacity_gb (int | None | Unset):
     """

    condition: ResolutionCondition
    mpn: str
    capacity_gb: int | None | Unset = UNSET





    def to_dict(self) -> dict[str, Any]:
        condition: str = self.condition

        mpn = self.mpn

        capacity_gb: int | None | Unset
        if isinstance(self.capacity_gb, Unset):
            capacity_gb = UNSET
        else:
            capacity_gb = self.capacity_gb


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "condition": condition,
            "mpn": mpn,
        })
        if capacity_gb is not UNSET:
            field_dict["capacity_gb"] = capacity_gb

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        condition = check_resolution_condition(d.pop("condition"))




        mpn = d.pop("mpn")

        def _parse_capacity_gb(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        capacity_gb = _parse_capacity_gb(d.pop("capacity_gb", UNSET))


        resolution = cls(
            condition=condition,
            mpn=mpn,
            capacity_gb=capacity_gb,
        )

        return resolution
