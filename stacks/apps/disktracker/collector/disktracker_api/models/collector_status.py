from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
import datetime

if TYPE_CHECKING:
  from ..models.running_activity import RunningActivity





T = TypeVar("T", bound="CollectorStatus")



@_attrs_define
class CollectorStatus:
    """ What the collector is doing: when it was last heard from (never: None), the runs in
    progress, and the keys of the sources waiting to run, in the order they will.

        Attributes:
            running (list[RunningActivity]):
            seen_at (datetime.datetime | None):
            waiting (list[str]):
     """

    running: list[RunningActivity]
    seen_at: datetime.datetime | None
    waiting: list[str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.running_activity import RunningActivity # noqa: PLC0415
        running = []
        for running_item_data in self.running:
            running_item = running_item_data.to_dict()
            running.append(running_item)



        seen_at: None | str
        if isinstance(self.seen_at, datetime.datetime):
            seen_at = self.seen_at.isoformat()
        else:
            seen_at = self.seen_at

        waiting = self.waiting




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "running": running,
            "seen_at": seen_at,
            "waiting": waiting,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.running_activity import RunningActivity # noqa: PLC0415
        d = dict(src_dict)
        running = []
        _running = d.pop("running")
        for running_item_data in (_running):
            running_item = RunningActivity.from_dict(running_item_data)



            running.append(running_item)


        def _parse_seen_at(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                seen_at_type_0 = datetime.datetime.fromisoformat(data)



                return seen_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        seen_at = _parse_seen_at(d.pop("seen_at"))


        waiting = cast(list[str], d.pop("waiting"))


        collector_status = cls(
            running=running,
            seen_at=seen_at,
            waiting=waiting,
        )


        collector_status.additional_properties = d
        return collector_status

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
