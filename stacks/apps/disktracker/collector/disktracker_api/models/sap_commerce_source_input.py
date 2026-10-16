from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.sap_commerce_source_input_basis import check_sap_commerce_source_input_basis
from ..models.sap_commerce_source_input_basis import SapCommerceSourceInputBasis
from ..models.sap_commerce_source_input_transport import check_sap_commerce_source_input_transport
from ..models.sap_commerce_source_input_transport import SapCommerceSourceInputTransport
from ..types import UNSET, Unset
from typing import cast
from typing import Literal, cast

if TYPE_CHECKING:
  from ..models.sap_commerce_settings_input import SapCommerceSettingsInput





T = TypeVar("T", bound="SapCommerceSourceInput")



@_attrs_define
class SapCommerceSourceInput:
    """
        Attributes:
            kind (Literal['sap_commerce']):
            name (str):
            base_url (str | Unset): Store HTTP(S) base URL, required for collected kinds; optional for manual sources.
                Default: ''.
            basis (SapCommerceSourceInputBasis | Unset):  Default: 'unconfirmed'.
            enabled (bool | Unset):  Default: True.
            notes (str | Unset):  Default: ''.
            obey_robots (bool | Unset): False lets the collector read pages robots.txt disallows; only with basis
                permission. Default: True.
            schedule (str | Unset): Five-field cron schedule evaluated in UTC; default runs every eight hours. Default: '0
                */8 * * *'.
            settings (SapCommerceSettingsInput | Unset):
            transport (SapCommerceSourceInputTransport | Unset):  Default: 'direct'.
     """

    kind: Literal['sap_commerce']
    name: str
    base_url: str | Unset = ''
    basis: SapCommerceSourceInputBasis | Unset = 'unconfirmed'
    enabled: bool | Unset = True
    notes: str | Unset = ''
    obey_robots: bool | Unset = True
    schedule: str | Unset = '0 */8 * * *'
    settings: SapCommerceSettingsInput | Unset = UNSET
    transport: SapCommerceSourceInputTransport | Unset = 'direct'





    def to_dict(self) -> dict[str, Any]:
        from ..models.sap_commerce_settings_input import SapCommerceSettingsInput # noqa: PLC0415
        kind = self.kind

        name = self.name

        base_url = self.base_url

        basis: str | Unset = UNSET
        if not isinstance(self.basis, Unset):
            basis = self.basis


        enabled = self.enabled

        notes = self.notes

        obey_robots = self.obey_robots

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
        if obey_robots is not UNSET:
            field_dict["obey_robots"] = obey_robots
        if schedule is not UNSET:
            field_dict["schedule"] = schedule
        if settings is not UNSET:
            field_dict["settings"] = settings
        if transport is not UNSET:
            field_dict["transport"] = transport

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sap_commerce_settings_input import SapCommerceSettingsInput # noqa: PLC0415
        d = dict(src_dict)
        kind = cast(Literal['sap_commerce'] , d.pop("kind"))
        if kind != 'sap_commerce':
            raise ValueError(f"kind must match const 'sap_commerce', got '{kind}'")

        name = d.pop("name")

        base_url = d.pop("base_url", UNSET)

        _basis = d.pop("basis", UNSET)
        basis: SapCommerceSourceInputBasis | Unset
        if isinstance(_basis,  Unset):
            basis = UNSET
        else:
            basis = check_sap_commerce_source_input_basis(_basis)




        enabled = d.pop("enabled", UNSET)

        notes = d.pop("notes", UNSET)

        obey_robots = d.pop("obey_robots", UNSET)

        schedule = d.pop("schedule", UNSET)

        _settings = d.pop("settings", UNSET)
        settings: SapCommerceSettingsInput | Unset
        if isinstance(_settings,  Unset):
            settings = UNSET
        else:
            settings = SapCommerceSettingsInput.from_dict(_settings)




        _transport = d.pop("transport", UNSET)
        transport: SapCommerceSourceInputTransport | Unset
        if isinstance(_transport,  Unset):
            transport = UNSET
        else:
            transport = check_sap_commerce_source_input_transport(_transport)




        sap_commerce_source_input = cls(
            kind=kind,
            name=name,
            base_url=base_url,
            basis=basis,
            enabled=enabled,
            notes=notes,
            obey_robots=obey_robots,
            schedule=schedule,
            settings=settings,
            transport=transport,
        )

        return sap_commerce_source_input
