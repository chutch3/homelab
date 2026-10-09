from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.source_preview_status import check_source_preview_status
from ..models.source_preview_status import SourcePreviewStatus
from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.preview_offer import PreviewOffer
  from ..models.preview_verdict import PreviewVerdict





T = TypeVar("T", bound="SourcePreview")



@_attrs_define
class SourcePreview:
    """
        Attributes:
            offer (None | PreviewOffer):
            reason (None | str):
            status (SourcePreviewStatus):
            verdict (None | PreviewVerdict):
            notes (list[str] | Unset):
     """

    offer: None | PreviewOffer
    reason: None | str
    status: SourcePreviewStatus
    verdict: None | PreviewVerdict
    notes: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.preview_offer import PreviewOffer # noqa: PLC0415
        from ..models.preview_verdict import PreviewVerdict # noqa: PLC0415
        offer: dict[str, Any] | None
        if isinstance(self.offer, PreviewOffer):
            offer = self.offer.to_dict()
        else:
            offer = self.offer

        reason: None | str
        reason = self.reason

        status: str = self.status

        verdict: dict[str, Any] | None
        if isinstance(self.verdict, PreviewVerdict):
            verdict = self.verdict.to_dict()
        else:
            verdict = self.verdict

        notes: list[str] | Unset = UNSET
        if not isinstance(self.notes, Unset):
            notes = self.notes




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "offer": offer,
            "reason": reason,
            "status": status,
            "verdict": verdict,
        })
        if notes is not UNSET:
            field_dict["notes"] = notes

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.preview_offer import PreviewOffer # noqa: PLC0415
        from ..models.preview_verdict import PreviewVerdict # noqa: PLC0415
        d = dict(src_dict)
        def _parse_offer(data: object) -> None | PreviewOffer:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                offer_type_0 = PreviewOffer.from_dict(data)



                return offer_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | PreviewOffer, data)

        offer = _parse_offer(d.pop("offer"))


        def _parse_reason(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        reason = _parse_reason(d.pop("reason"))


        status = check_source_preview_status(d.pop("status"))




        def _parse_verdict(data: object) -> None | PreviewVerdict:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                verdict_type_0 = PreviewVerdict.from_dict(data)



                return verdict_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | PreviewVerdict, data)

        verdict = _parse_verdict(d.pop("verdict"))


        notes = cast(list[str], d.pop("notes", UNSET))


        source_preview = cls(
            offer=offer,
            reason=reason,
            status=status,
            verdict=verdict,
            notes=notes,
        )


        source_preview.additional_properties = d
        return source_preview

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
