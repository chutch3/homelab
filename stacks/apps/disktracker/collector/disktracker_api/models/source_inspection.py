from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.source_inspection_status import check_source_inspection_status
from ..models.source_inspection_status import SourceInspectionStatus
from typing import cast

if TYPE_CHECKING:
  from ..models.sap_commerce_candidate import SapCommerceCandidate
  from ..models.shopify_candidate import ShopifyCandidate
  from ..models.sitemap_candidate import SitemapCandidate





T = TypeVar("T", bound="SourceInspection")



@_attrs_define
class SourceInspection:
    """
        Attributes:
            base_url (str):
            candidates (list[SapCommerceCandidate | ShopifyCandidate | SitemapCandidate]):
            notes (list[str]):
            reason (None | str):
            status (SourceInspectionStatus):
     """

    base_url: str
    candidates: list[SapCommerceCandidate | ShopifyCandidate | SitemapCandidate]
    notes: list[str]
    reason: None | str
    status: SourceInspectionStatus
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.sap_commerce_candidate import SapCommerceCandidate # noqa: PLC0415
        from ..models.shopify_candidate import ShopifyCandidate # noqa: PLC0415
        from ..models.sitemap_candidate import SitemapCandidate # noqa: PLC0415
        base_url = self.base_url

        candidates = []
        for candidates_item_data in self.candidates:
            candidates_item: dict[str, Any]
            if isinstance(candidates_item_data, ShopifyCandidate):
                candidates_item = candidates_item_data.to_dict()
            elif isinstance(candidates_item_data, SitemapCandidate):
                candidates_item = candidates_item_data.to_dict()
            else:
                candidates_item = candidates_item_data.to_dict()

            candidates.append(candidates_item)



        notes = self.notes



        reason: None | str
        reason = self.reason

        status: str = self.status


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "base_url": base_url,
            "candidates": candidates,
            "notes": notes,
            "reason": reason,
            "status": status,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sap_commerce_candidate import SapCommerceCandidate # noqa: PLC0415
        from ..models.shopify_candidate import ShopifyCandidate # noqa: PLC0415
        from ..models.sitemap_candidate import SitemapCandidate # noqa: PLC0415
        d = dict(src_dict)
        base_url = d.pop("base_url")

        candidates = []
        _candidates = d.pop("candidates")
        for candidates_item_data in (_candidates):
            def _parse_candidates_item(data: object) -> SapCommerceCandidate | ShopifyCandidate | SitemapCandidate:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    candidates_item_type_0 = ShopifyCandidate.from_dict(data)



                    return candidates_item_type_0
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    candidates_item_type_1 = SitemapCandidate.from_dict(data)



                    return candidates_item_type_1
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                candidates_item_type_2 = SapCommerceCandidate.from_dict(data)



                return candidates_item_type_2

            candidates_item = _parse_candidates_item(candidates_item_data)

            candidates.append(candidates_item)


        notes = cast(list[str], d.pop("notes"))


        def _parse_reason(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        reason = _parse_reason(d.pop("reason"))


        status = check_source_inspection_status(d.pop("status"))




        source_inspection = cls(
            base_url=base_url,
            candidates=candidates,
            notes=notes,
            reason=reason,
            status=status,
        )


        source_inspection.additional_properties = d
        return source_inspection

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
