from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.sap_commerce_source_preview_input_basis import check_sap_commerce_source_preview_input_basis
from ..models.sap_commerce_source_preview_input_basis import SapCommerceSourcePreviewInputBasis
from ..models.sap_commerce_source_preview_input_transport import check_sap_commerce_source_preview_input_transport
from ..models.sap_commerce_source_preview_input_transport import SapCommerceSourcePreviewInputTransport
from ..types import UNSET, Unset
from typing import cast
from typing import Literal, cast

if TYPE_CHECKING:
  from ..models.sap_commerce_settings_input import SapCommerceSettingsInput





T = TypeVar("T", bound="SapCommerceSourcePreviewInput")



@_attrs_define
class SapCommerceSourcePreviewInput:
    """
        Attributes:
            base_url (str): Store HTTP(S) base URL.
            kind (Literal['sap_commerce']):
            name (str):
            settings (SapCommerceSettingsInput):
            basis (SapCommerceSourcePreviewInputBasis | Unset):  Default: 'unconfirmed'.
            enabled (bool | Unset):  Default: True.
            notes (str | Unset):  Default: ''.
            obey_robots (bool | Unset): False lets the collector read pages robots.txt disallows; only with basis
                permission. Default: True.
            page_url (str | Unset):  Default: ''.
            schedule (str | Unset): Five-field cron schedule evaluated in UTC; default runs every eight hours. Default: '0
                */8 * * *'.
            transport (SapCommerceSourcePreviewInputTransport | Unset):  Default: 'direct'.
     """

    base_url: str
    kind: Literal['sap_commerce']
    name: str
    settings: SapCommerceSettingsInput
    basis: SapCommerceSourcePreviewInputBasis | Unset = 'unconfirmed'
    enabled: bool | Unset = True
    notes: str | Unset = ''
    obey_robots: bool | Unset = True
    page_url: str | Unset = ''
    schedule: str | Unset = '0 */8 * * *'
    transport: SapCommerceSourcePreviewInputTransport | Unset = 'direct'





    def to_dict(self) -> dict[str, Any]:
        from ..models.sap_commerce_settings_input import SapCommerceSettingsInput # noqa: PLC0415
        base_url = self.base_url

        kind = self.kind

        name = self.name

        settings = self.settings.to_dict()

        basis: str | Unset = UNSET
        if not isinstance(self.basis, Unset):
            basis = self.basis


        enabled = self.enabled

        notes = self.notes

        obey_robots = self.obey_robots

        page_url = self.page_url

        schedule = self.schedule

        transport: str | Unset = UNSET
        if not isinstance(self.transport, Unset):
            transport = self.transport



        field_dict: dict[str, Any] = {}

        field_dict.update({
            "base_url": base_url,
            "kind": kind,
            "name": name,
            "settings": settings,
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
        if transport is not UNSET:
            field_dict["transport"] = transport

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sap_commerce_settings_input import SapCommerceSettingsInput # noqa: PLC0415
        d = dict(src_dict)
        base_url = d.pop("base_url")

        kind = cast(Literal['sap_commerce'] , d.pop("kind"))
        if kind != 'sap_commerce':
            raise ValueError(f"kind must match const 'sap_commerce', got '{kind}'")

        name = d.pop("name")

        settings = SapCommerceSettingsInput.from_dict(d.pop("settings"))




        _basis = d.pop("basis", UNSET)
        basis: SapCommerceSourcePreviewInputBasis | Unset
        if isinstance(_basis,  Unset):
            basis = UNSET
        else:
            basis = check_sap_commerce_source_preview_input_basis(_basis)




        enabled = d.pop("enabled", UNSET)

        notes = d.pop("notes", UNSET)

        obey_robots = d.pop("obey_robots", UNSET)

        page_url = d.pop("page_url", UNSET)

        schedule = d.pop("schedule", UNSET)

        _transport = d.pop("transport", UNSET)
        transport: SapCommerceSourcePreviewInputTransport | Unset
        if isinstance(_transport,  Unset):
            transport = UNSET
        else:
            transport = check_sap_commerce_source_preview_input_transport(_transport)




        sap_commerce_source_preview_input = cls(
            base_url=base_url,
            kind=kind,
            name=name,
            settings=settings,
            basis=basis,
            enabled=enabled,
            notes=notes,
            obey_robots=obey_robots,
            page_url=page_url,
            schedule=schedule,
            transport=transport,
        )

        return sap_commerce_source_preview_input
