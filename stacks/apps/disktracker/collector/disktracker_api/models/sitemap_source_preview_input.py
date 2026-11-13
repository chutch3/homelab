from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.sitemap_source_preview_input_basis import check_sitemap_source_preview_input_basis
from ..models.sitemap_source_preview_input_basis import SitemapSourcePreviewInputBasis
from ..models.sitemap_source_preview_input_transport import check_sitemap_source_preview_input_transport
from ..models.sitemap_source_preview_input_transport import SitemapSourcePreviewInputTransport
from ..types import UNSET, Unset
from typing import cast
from typing import Literal, cast

if TYPE_CHECKING:
  from ..models.sitemap_settings_input import SitemapSettingsInput





T = TypeVar("T", bound="SitemapSourcePreviewInput")



@_attrs_define
class SitemapSourcePreviewInput:
    """
        Attributes:
            base_url (str): Store HTTP(S) base URL.
            kind (Literal['sitemap']):
            name (str):
            basis (SitemapSourcePreviewInputBasis | Unset):  Default: 'unconfirmed'.
            enabled (bool | Unset):  Default: True.
            notes (str | Unset):  Default: ''.
            obey_robots (bool | Unset): False lets the collector read pages robots.txt disallows; only with basis
                permission. Default: True.
            page_url (str | Unset):  Default: ''.
            schedule (str | Unset): Five-field cron schedule evaluated in UTC; default runs every eight hours. Default: '0
                */8 * * *'.
            settings (SitemapSettingsInput | Unset):
            transport (SitemapSourcePreviewInputTransport | Unset):  Default: 'direct'.
     """

    base_url: str
    kind: Literal['sitemap']
    name: str
    basis: SitemapSourcePreviewInputBasis | Unset = 'unconfirmed'
    enabled: bool | Unset = True
    notes: str | Unset = ''
    obey_robots: bool | Unset = True
    page_url: str | Unset = ''
    schedule: str | Unset = '0 */8 * * *'
    settings: SitemapSettingsInput | Unset = UNSET
    transport: SitemapSourcePreviewInputTransport | Unset = 'direct'





    def to_dict(self) -> dict[str, Any]:
        from ..models.sitemap_settings_input import SitemapSettingsInput # noqa: PLC0415
        base_url = self.base_url

        kind = self.kind

        name = self.name

        basis: str | Unset = UNSET
        if not isinstance(self.basis, Unset):
            basis = self.basis


        enabled = self.enabled

        notes = self.notes

        obey_robots = self.obey_robots

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
            "base_url": base_url,
            "kind": kind,
            "name": name,
        })
        if basis is not UNSET:
            field_dict["basis"] = basis
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if notes is not UNSET:
            field_dict["notes"] = notes
        if obey_robots is not UNSET:
            field_dict["obey_robots"] = obey_robots
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
        from ..models.sitemap_settings_input import SitemapSettingsInput # noqa: PLC0415
        d = dict(src_dict)
        base_url = d.pop("base_url")

        kind = cast(Literal['sitemap'] , d.pop("kind"))
        if kind != 'sitemap':
            raise ValueError(f"kind must match const 'sitemap', got '{kind}'")

        name = d.pop("name")

        _basis = d.pop("basis", UNSET)
        basis: SitemapSourcePreviewInputBasis | Unset
        if isinstance(_basis,  Unset):
            basis = UNSET
        else:
            basis = check_sitemap_source_preview_input_basis(_basis)




        enabled = d.pop("enabled", UNSET)

        notes = d.pop("notes", UNSET)

        obey_robots = d.pop("obey_robots", UNSET)

        page_url = d.pop("page_url", UNSET)

        schedule = d.pop("schedule", UNSET)

        _settings = d.pop("settings", UNSET)
        settings: SitemapSettingsInput | Unset
        if isinstance(_settings,  Unset):
            settings = UNSET
        else:
            settings = SitemapSettingsInput.from_dict(_settings)




        _transport = d.pop("transport", UNSET)
        transport: SitemapSourcePreviewInputTransport | Unset
        if isinstance(_transport,  Unset):
            transport = UNSET
        else:
            transport = check_sitemap_source_preview_input_transport(_transport)




        sitemap_source_preview_input = cls(
            base_url=base_url,
            kind=kind,
            name=name,
            basis=basis,
            enabled=enabled,
            notes=notes,
            obey_robots=obey_robots,
            page_url=page_url,
            schedule=schedule,
            settings=settings,
            transport=transport,
        )

        return sitemap_source_preview_input
