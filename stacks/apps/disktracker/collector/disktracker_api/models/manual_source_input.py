from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.manual_source_input_basis import check_manual_source_input_basis
from ..models.manual_source_input_basis import ManualSourceInputBasis
from ..models.manual_source_input_transport import check_manual_source_input_transport
from ..models.manual_source_input_transport import ManualSourceInputTransport
from ..types import UNSET, Unset
from typing import cast
from typing import Literal, cast

if TYPE_CHECKING:
  from ..models.manual_settings import ManualSettings





T = TypeVar("T", bound="ManualSourceInput")



@_attrs_define
class ManualSourceInput:
    """
        Attributes:
            kind (Literal['manual']):
            name (str):
            base_url (str | Unset): Store HTTP(S) base URL, required for collected kinds; optional for manual sources.
                Default: ''.
            basis (ManualSourceInputBasis | Unset):  Default: 'unconfirmed'.
            enabled (bool | Unset):  Default: True.
            notes (str | Unset):  Default: ''.
            obey_robots (bool | Unset): False lets the collector read pages robots.txt disallows; only with basis
                permission. Default: True.
            schedule (str | Unset): Five-field cron schedule evaluated in UTC; default runs every eight hours. Default: '0
                */8 * * *'.
            settings (ManualSettings | Unset): A store entered by hand has nothing to set.
            transport (ManualSourceInputTransport | Unset):  Default: 'direct'.
     """

    kind: Literal['manual']
    name: str
    base_url: str | Unset = ''
    basis: ManualSourceInputBasis | Unset = 'unconfirmed'
    enabled: bool | Unset = True
    notes: str | Unset = ''
    obey_robots: bool | Unset = True
    schedule: str | Unset = '0 */8 * * *'
    settings: ManualSettings | Unset = UNSET
    transport: ManualSourceInputTransport | Unset = 'direct'





    def to_dict(self) -> dict[str, Any]:
        from ..models.manual_settings import ManualSettings # noqa: PLC0415
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
        from ..models.manual_settings import ManualSettings # noqa: PLC0415
        d = dict(src_dict)
        kind = cast(Literal['manual'] , d.pop("kind"))
        if kind != 'manual':
            raise ValueError(f"kind must match const 'manual', got '{kind}'")

        name = d.pop("name")

        base_url = d.pop("base_url", UNSET)

        _basis = d.pop("basis", UNSET)
        basis: ManualSourceInputBasis | Unset
        if isinstance(_basis,  Unset):
            basis = UNSET
        else:
            basis = check_manual_source_input_basis(_basis)




        enabled = d.pop("enabled", UNSET)

        notes = d.pop("notes", UNSET)

        obey_robots = d.pop("obey_robots", UNSET)

        schedule = d.pop("schedule", UNSET)

        _settings = d.pop("settings", UNSET)
        settings: ManualSettings | Unset
        if isinstance(_settings,  Unset):
            settings = UNSET
        else:
            settings = ManualSettings.from_dict(_settings)




        _transport = d.pop("transport", UNSET)
        transport: ManualSourceInputTransport | Unset
        if isinstance(_transport,  Unset):
            transport = UNSET
        else:
            transport = check_manual_source_input_transport(_transport)




        manual_source_input = cls(
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

        return manual_source_input
