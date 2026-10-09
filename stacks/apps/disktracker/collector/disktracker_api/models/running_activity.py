from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
import datetime






T = TypeVar("T", bound="RunningActivity")



@_attrs_define
class RunningActivity:
    """ A run in progress, and when the collector last said how far it had got.

        Attributes:
            failed (int):
            ignored (int):
            queued (int):
            recorded (int):
            seen (int):
            source (str):
            started_at (datetime.datetime):
            updated_at (datetime.datetime):
     """

    failed: int
    ignored: int
    queued: int
    recorded: int
    seen: int
    source: str
    started_at: datetime.datetime
    updated_at: datetime.datetime





    def to_dict(self) -> dict[str, Any]:
        failed = self.failed

        ignored = self.ignored

        queued = self.queued

        recorded = self.recorded

        seen = self.seen

        source = self.source

        started_at = self.started_at.isoformat()

        updated_at = self.updated_at.isoformat()


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "failed": failed,
            "ignored": ignored,
            "queued": queued,
            "recorded": recorded,
            "seen": seen,
            "source": source,
            "started_at": started_at,
            "updated_at": updated_at,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        failed = d.pop("failed")

        ignored = d.pop("ignored")

        queued = d.pop("queued")

        recorded = d.pop("recorded")

        seen = d.pop("seen")

        source = d.pop("source")

        started_at = datetime.datetime.fromisoformat(d.pop("started_at"))




        updated_at = datetime.datetime.fromisoformat(d.pop("updated_at"))




        running_activity = cls(
            failed=failed,
            ignored=ignored,
            queued=queued,
            recorded=recorded,
            seen=seen,
            source=source,
            started_at=started_at,
            updated_at=updated_at,
        )

        return running_activity
