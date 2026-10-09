from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.source_input_basis import check_source_input_basis
from ..models.source_input_basis import SourceInputBasis
from ..models.source_input_transport import check_source_input_transport
from ..models.source_input_transport import SourceInputTransport
from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.source_input_settings import SourceInputSettings





T = TypeVar("T", bound="SourceInput")



@_attrs_define
class SourceInput:
    """ A store offers are recorded under: its kind (how the collector reads it, or entered by
    hand), its address, and when it is collected. Its key is fixed from its name.

        Attributes:
            kind (str):
            name (str):
            base_url (str | Unset):  Default: ''.
            basis (SourceInputBasis | Unset):  Default: 'unconfirmed'.
            enabled (bool | Unset):  Default: True.
            notes (str | Unset):  Default: ''.
            schedule (str | Unset):  Default: '0 */8 * * *'.
            settings (SourceInputSettings | Unset):
            transport (SourceInputTransport | Unset):  Default: 'direct'.
     """

    kind: str
    name: str
    base_url: str | Unset = ''
    basis: SourceInputBasis | Unset = 'unconfirmed'
    enabled: bool | Unset = True
    notes: str | Unset = ''
    schedule: str | Unset = '0 */8 * * *'
    settings: SourceInputSettings | Unset = UNSET
    transport: SourceInputTransport | Unset = 'direct'





    def to_dict(self) -> dict[str, Any]:
        from ..models.source_input_settings import SourceInputSettings # noqa: PLC0415
        kind = self.kind

        name = self.name

        base_url = self.base_url

        basis: str | Unset = UNSET
        if not isinstance(self.basis, Unset):
            basis = self.basis


        enabled = self.enabled

        notes = self.notes

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
        if schedule is not UNSET:
            field_dict["schedule"] = schedule
        if settings is not UNSET:
            field_dict["settings"] = settings
        if transport is not UNSET:
            field_dict["transport"] = transport

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.source_input_settings import SourceInputSettings # noqa: PLC0415
        d = dict(src_dict)
        kind = d.pop("kind")

        name = d.pop("name")

        base_url = d.pop("base_url", UNSET)

        _basis = d.pop("basis", UNSET)
        basis: SourceInputBasis | Unset
        if isinstance(_basis,  Unset):
            basis = UNSET
        else:
            basis = check_source_input_basis(_basis)




        enabled = d.pop("enabled", UNSET)

        notes = d.pop("notes", UNSET)

        schedule = d.pop("schedule", UNSET)

        _settings = d.pop("settings", UNSET)
        settings: SourceInputSettings | Unset
        if isinstance(_settings,  Unset):
            settings = UNSET
        else:
            settings = SourceInputSettings.from_dict(_settings)




        _transport = d.pop("transport", UNSET)
        transport: SourceInputTransport | Unset
        if isinstance(_transport,  Unset):
            transport = UNSET
        else:
            transport = check_source_input_transport(_transport)




        source_input = cls(
            kind=kind,
            name=name,
            base_url=base_url,
            basis=basis,
            enabled=enabled,
            notes=notes,
            schedule=schedule,
            settings=settings,
            transport=transport,
        )

        return source_input
