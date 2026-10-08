from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.source_preview_input_basis import check_source_preview_input_basis
from ..models.source_preview_input_basis import SourcePreviewInputBasis
from ..models.source_preview_input_transport import check_source_preview_input_transport
from ..models.source_preview_input_transport import SourcePreviewInputTransport
from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.source_preview_input_settings import SourcePreviewInputSettings





T = TypeVar("T", bound="SourcePreviewInput")



@_attrs_define
class SourcePreviewInput:
    """ A source to try, saved or not. page_url: one of its pages to read instead of those its
    sitemap lists, so its settings can be tried on a page known to offer a drive.

        Attributes:
            kind (str):
            name (str):
            base_url (str | Unset):  Default: ''.
            basis (SourcePreviewInputBasis | Unset):  Default: 'unconfirmed'.
            enabled (bool | Unset):  Default: True.
            notes (str | Unset):  Default: ''.
            page_url (str | Unset):  Default: ''.
            schedule (str | Unset):  Default: '0 */8 * * *'.
            settings (SourcePreviewInputSettings | Unset):
            transport (SourcePreviewInputTransport | Unset):  Default: 'direct'.
     """

    kind: str
    name: str
    base_url: str | Unset = ''
    basis: SourcePreviewInputBasis | Unset = 'unconfirmed'
    enabled: bool | Unset = True
    notes: str | Unset = ''
    page_url: str | Unset = ''
    schedule: str | Unset = '0 */8 * * *'
    settings: SourcePreviewInputSettings | Unset = UNSET
    transport: SourcePreviewInputTransport | Unset = 'direct'





    def to_dict(self) -> dict[str, Any]:
        from ..models.source_preview_input_settings import SourcePreviewInputSettings # noqa: PLC0415
        kind = self.kind

        name = self.name

        base_url = self.base_url

        basis: str | Unset = UNSET
        if not isinstance(self.basis, Unset):
            basis = self.basis


        enabled = self.enabled

        notes = self.notes

        page_url = self.page_url

        schedule = self.schedule

        settings: dict[str, Any] | Unset = UNSET
        if not isinstance(self.settings, Unset):
            settings = self.settings.to_dict()

        transport: str | Unset = UNSET
        if not isinstance(self.transport, Unset):
            transport = self.transport



        field_dict: dict[str, Any] = {}

        field_dict.update({
            "kind": kind,
            "name": name,
        })
        if base_url is not UNSET:
            field_dict["base_url"] = base_url
        if basis is not UNSET:
            field_dict["basis"] = basis
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if notes is not UNSET:
            field_dict["notes"] = notes
        if page_url is not UNSET:
            field_dict["page_url"] = page_url
        if schedule is not UNSET:
            field_dict["schedule"] = schedule
        if settings is not UNSET:
            field_dict["settings"] = settings
        if transport is not UNSET:
            field_dict["transport"] = transport

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.source_preview_input_settings import SourcePreviewInputSettings # noqa: PLC0415
        d = dict(src_dict)
        kind = d.pop("kind")

        name = d.pop("name")

        base_url = d.pop("base_url", UNSET)

        _basis = d.pop("basis", UNSET)
        basis: SourcePreviewInputBasis | Unset
        if isinstance(_basis,  Unset):
            basis = UNSET
        else:
            basis = check_source_preview_input_basis(_basis)




        enabled = d.pop("enabled", UNSET)

        notes = d.pop("notes", UNSET)

        page_url = d.pop("page_url", UNSET)

        schedule = d.pop("schedule", UNSET)

        _settings = d.pop("settings", UNSET)
        settings: SourcePreviewInputSettings | Unset
        if isinstance(_settings,  Unset):
            settings = UNSET
        else:
            settings = SourcePreviewInputSettings.from_dict(_settings)




        _transport = d.pop("transport", UNSET)
        transport: SourcePreviewInputTransport | Unset
        if isinstance(_transport,  Unset):
            transport = UNSET
        else:
            transport = check_source_preview_input_transport(_transport)




        source_preview_input = cls(
            kind=kind,
            name=name,
            base_url=base_url,
            basis=basis,
            enabled=enabled,
            notes=notes,
            page_url=page_url,
            schedule=schedule,
            settings=settings,
            transport=transport,
        )

        return source_preview_input
