from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
import datetime






T = TypeVar("T", bound="Activity")



@_attrs_define
class Activity:
    """ How far a run in progress has got, as the collector says while it runs.

        Attributes:
            failed (int):
            ignored (int):
            queued (int):
            recorded (int):
            seen (int):
            source (str):
            started_at (datetime.datetime):
     """

    failed: int
    ignored: int
    queued: int
    recorded: int
    seen: int
    source: str
    started_at: datetime.datetime





    def to_dict(self) -> dict[str, Any]:
        failed = self.failed

        ignored = self.ignored

        queued = self.queued

        recorded = self.recorded

        seen = self.seen

        source = self.source

        started_at = self.started_at.isoformat()


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "failed": failed,
            "ignored": ignored,
            "queued": queued,
            "recorded": recorded,
            "seen": seen,
            "source": source,
            "started_at": started_at,
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




        activity = cls(
            failed=failed,
            ignored=ignored,
            queued=queued,
            recorded=recorded,
            seen=seen,
            source=source,
            started_at=started_at,
        )

        return activity
