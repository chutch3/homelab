from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.manual_source_view_basis import check_manual_source_view_basis
from ..models.manual_source_view_basis import ManualSourceViewBasis
from ..models.manual_source_view_transport import check_manual_source_view_transport
from ..models.manual_source_view_transport import ManualSourceViewTransport
from typing import cast
from typing import Literal, cast
from uuid import UUID
import datetime

if TYPE_CHECKING:
  from ..models.manual_settings import ManualSettings





T = TypeVar("T", bound="ManualSourceView")



@_attrs_define
class ManualSourceView:
    """
        Attributes:
            base_url (str):
            basis (ManualSourceViewBasis):
            enabled (bool):
            id (UUID):
            key (str): Stable source key used by prices and runs; distinct from this source UUID.
            kind (Literal['manual']):
            name (str):
            next_run_at (datetime.datetime | None):
            notes (str):
            obey_robots (bool):
            schedule (str):
            settings (ManualSettings): A store entered by hand has nothing to set.
            transport (ManualSourceViewTransport):
     """

    base_url: str
    basis: ManualSourceViewBasis
    enabled: bool
    id: UUID
    key: str
    kind: Literal['manual']
    name: str
    next_run_at: datetime.datetime | None
    notes: str
    obey_robots: bool
    schedule: str
    settings: ManualSettings
    transport: ManualSourceViewTransport
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.manual_settings import ManualSettings # noqa: PLC0415
        base_url = self.base_url

        basis: str = self.basis

        enabled = self.enabled

        id = str(self.id)

        key = self.key

        kind = self.kind

        name = self.name

        next_run_at: None | str
        if isinstance(self.next_run_at, datetime.datetime):
            next_run_at = self.next_run_at.isoformat()
        else:
            next_run_at = self.next_run_at

        notes = self.notes

        obey_robots = self.obey_robots

        schedule = self.schedule

        settings = self.settings.to_dict()

        transport: str = self.transport


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "base_url": base_url,
            "basis": basis,
            "enabled": enabled,
            "id": id,
            "key": key,
            "kind": kind,
            "name": name,
            "next_run_at": next_run_at,
            "notes": notes,
            "obey_robots": obey_robots,
            "schedule": schedule,
            "settings": settings,
            "transport": transport,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.manual_settings import ManualSettings # noqa: PLC0415
        d = dict(src_dict)
        base_url = d.pop("base_url")

        basis = check_manual_source_view_basis(d.pop("basis"))




        enabled = d.pop("enabled")

        id = UUID(d.pop("id"))




        key = d.pop("key")

        kind = cast(Literal['manual'] , d.pop("kind"))
        if kind != 'manual':
            raise ValueError(f"kind must match const 'manual', got '{kind}'")

        name = d.pop("name")

        def _parse_next_run_at(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                next_run_at_type_0 = datetime.datetime.fromisoformat(data)



                return next_run_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        next_run_at = _parse_next_run_at(d.pop("next_run_at"))


        notes = d.pop("notes")

        obey_robots = d.pop("obey_robots")

        schedule = d.pop("schedule")

        settings = ManualSettings.from_dict(d.pop("settings"))




        transport = check_manual_source_view_transport(d.pop("transport"))




        manual_source_view = cls(
            base_url=base_url,
            basis=basis,
            enabled=enabled,
            id=id,
            key=key,
            kind=kind,
            name=name,
            next_run_at=next_run_at,
            notes=notes,
            obey_robots=obey_robots,
            schedule=schedule,
            settings=settings,
            transport=transport,
        )


        manual_source_view.additional_properties = d
        return manual_source_view

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
