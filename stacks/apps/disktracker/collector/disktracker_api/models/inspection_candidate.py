from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.inspection_candidate_settings import InspectionCandidateSettings
  from ..models.preview_offer import PreviewOffer
  from ..models.preview_verdict import PreviewVerdict
  from ..models.store_fact import StoreFact





T = TypeVar("T", bound="InspectionCandidate")



@_attrs_define
class InspectionCandidate:
    """ One way of reading the store a link is from: the kind of source and its settings, why
    they were chosen, how many offers they read from the page, the first of them, and what
    disktracker would do with it.

        Attributes:
            evidence (list[str]):
            kind (str):
            offer (PreviewOffer): One offer as the collector read it from a source being tested; nothing is kept.
            offers (int):
            settings (InspectionCandidateSettings):
            verdict (PreviewVerdict): What disktracker would do with the offer: record it, hold it for review, or ignore it.
            summary (list[StoreFact] | Unset):
     """

    evidence: list[str]
    kind: str
    offer: PreviewOffer
    offers: int
    settings: InspectionCandidateSettings
    verdict: PreviewVerdict
    summary: list[StoreFact] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.inspection_candidate_settings import InspectionCandidateSettings # noqa: PLC0415
        from ..models.preview_offer import PreviewOffer # noqa: PLC0415
        from ..models.preview_verdict import PreviewVerdict # noqa: PLC0415
        from ..models.store_fact import StoreFact # noqa: PLC0415
        evidence = self.evidence



        kind = self.kind

        offer = self.offer.to_dict()

        offers = self.offers

        settings = self.settings.to_dict()

        verdict = self.verdict.to_dict()

        summary: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.summary, Unset):
            summary = []
            for summary_item_data in self.summary:
                summary_item = summary_item_data.to_dict()
                summary.append(summary_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "evidence": evidence,
            "kind": kind,
            "offer": offer,
            "offers": offers,
            "settings": settings,
            "verdict": verdict,
        })
        if summary is not UNSET:
            field_dict["summary"] = summary

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.inspection_candidate_settings import InspectionCandidateSettings # noqa: PLC0415
        from ..models.preview_offer import PreviewOffer # noqa: PLC0415
        from ..models.preview_verdict import PreviewVerdict # noqa: PLC0415
        from ..models.store_fact import StoreFact # noqa: PLC0415
        d = dict(src_dict)
        evidence = cast(list[str], d.pop("evidence"))


        kind = d.pop("kind")

        offer = PreviewOffer.from_dict(d.pop("offer"))




        offers = d.pop("offers")

        settings = InspectionCandidateSettings.from_dict(d.pop("settings"))




        verdict = PreviewVerdict.from_dict(d.pop("verdict"))




        _summary = d.pop("summary", UNSET)
        summary: list[StoreFact] | Unset = UNSET
        if _summary is not UNSET:
            summary = []
            for summary_item_data in _summary:
                summary_item = StoreFact.from_dict(summary_item_data)



                summary.append(summary_item)


        inspection_candidate = cls(
            evidence=evidence,
            kind=kind,
            offer=offer,
            offers=offers,
            settings=settings,
            verdict=verdict,
            summary=summary,
        )


        inspection_candidate.additional_properties = d
        return inspection_candidate

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
