from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
import datetime






T = TypeVar("T", bound="CollectorRun")



@_attrs_define
class CollectorRun:
    """ What one collector run of one source did, as the collector reports it.

        Attributes:
            completed (bool):
            failed (int):
            finished_at (datetime.datetime):
            ignored (int):
            queued (int):
            recheck_failed (int):
            rechecked (int):
            recorded (int):
            seen (int):
            source (str):
            started_at (datetime.datetime):
            stopped (bool | Unset):  Default: False.
     """

    completed: bool
    failed: int
    finished_at: datetime.datetime
    ignored: int
    queued: int
    recheck_failed: int
    rechecked: int
    recorded: int
    seen: int
    source: str
    started_at: datetime.datetime
    stopped: bool | Unset = False





    def to_dict(self) -> dict[str, Any]:
        completed = self.completed

        failed = self.failed

        finished_at = self.finished_at.isoformat()

        ignored = self.ignored

        queued = self.queued

        recheck_failed = self.recheck_failed

        rechecked = self.rechecked

        recorded = self.recorded

        seen = self.seen

        source = self.source

        started_at = self.started_at.isoformat()

        stopped = self.stopped


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "completed": completed,
            "failed": failed,
            "finished_at": finished_at,
            "ignored": ignored,
            "queued": queued,
            "recheck_failed": recheck_failed,
            "rechecked": rechecked,
            "recorded": recorded,
            "seen": seen,
            "source": source,
            "started_at": started_at,
        })
        if stopped is not UNSET:
            field_dict["stopped"] = stopped

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        completed = d.pop("completed")

        failed = d.pop("failed")

        finished_at = datetime.datetime.fromisoformat(d.pop("finished_at"))




        ignored = d.pop("ignored")

        queued = d.pop("queued")

        recheck_failed = d.pop("recheck_failed")

        rechecked = d.pop("rechecked")

        recorded = d.pop("recorded")

        seen = d.pop("seen")

        source = d.pop("source")

        started_at = datetime.datetime.fromisoformat(d.pop("started_at"))




        stopped = d.pop("stopped", UNSET)

        collector_run = cls(
            completed=completed,
            failed=failed,
            finished_at=finished_at,
            ignored=ignored,
            queued=queued,
            recheck_failed=recheck_failed,
            rechecked=rechecked,
            recorded=recorded,
            seen=seen,
            source=source,
            started_at=started_at,
            stopped=stopped,
        )

        return collector_run
