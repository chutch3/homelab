from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.run_status import check_run_status
from ..models.run_status import RunStatus
from typing import cast
from uuid import UUID
import datetime






T = TypeVar("T", bound="Run")



@_attrs_define
class Run:
    """ A run. stop_requested: its source was asked to stop since it started, so it should end
    here. reason: why it did not complete, when known: as its collector said for a failed run,
    as disktracker found it for an abandoned one.

        Attributes:
            failed (int):
            finished_at (datetime.datetime | None):
            id (UUID):
            ignored (int):
            queued (int):
            reason (None | str):
            recheck_failed (int):  Default: 0.
            rechecked (int):  Default: 0.
            recorded (int):
            seen (int):
            source (str):
            started_at (datetime.datetime):
            status (RunStatus):
            stop_requested (bool):
            updated_at (datetime.datetime):
     """

    failed: int
    finished_at: datetime.datetime | None
    id: UUID
    ignored: int
    queued: int
    reason: None | str
    recorded: int
    seen: int
    source: str
    started_at: datetime.datetime
    status: RunStatus
    stop_requested: bool
    updated_at: datetime.datetime
    recheck_failed: int = 0
    rechecked: int = 0





    def to_dict(self) -> dict[str, Any]:
        failed = self.failed

        finished_at: None | str
        if isinstance(self.finished_at, datetime.datetime):
            finished_at = self.finished_at.isoformat()
        else:
            finished_at = self.finished_at

        id = str(self.id)

        ignored = self.ignored

        queued = self.queued

        reason: None | str
        reason = self.reason

        recheck_failed = self.recheck_failed

        rechecked = self.rechecked

        recorded = self.recorded

        seen = self.seen

        source = self.source

        started_at = self.started_at.isoformat()

        status: str = self.status

        stop_requested = self.stop_requested

        updated_at = self.updated_at.isoformat()


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "failed": failed,
            "finished_at": finished_at,
            "id": id,
            "ignored": ignored,
            "queued": queued,
            "reason": reason,
            "recheck_failed": recheck_failed,
            "rechecked": rechecked,
            "recorded": recorded,
            "seen": seen,
            "source": source,
            "started_at": started_at,
            "status": status,
            "stop_requested": stop_requested,
            "updated_at": updated_at,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        failed = d.pop("failed")

        def _parse_finished_at(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                finished_at_type_0 = datetime.datetime.fromisoformat(data)



                return finished_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        finished_at = _parse_finished_at(d.pop("finished_at"))


        id = UUID(d.pop("id"))




        ignored = d.pop("ignored")

        queued = d.pop("queued")

        def _parse_reason(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        reason = _parse_reason(d.pop("reason"))


        recheck_failed = d.pop("recheck_failed")

        rechecked = d.pop("rechecked")

        recorded = d.pop("recorded")

        seen = d.pop("seen")

        source = d.pop("source")

        started_at = datetime.datetime.fromisoformat(d.pop("started_at"))




        status = check_run_status(d.pop("status"))




        stop_requested = d.pop("stop_requested")

        updated_at = datetime.datetime.fromisoformat(d.pop("updated_at"))




        run = cls(
            failed=failed,
            finished_at=finished_at,
            id=id,
            ignored=ignored,
            queued=queued,
            reason=reason,
            recheck_failed=recheck_failed,
            rechecked=rechecked,
            recorded=recorded,
            seen=seen,
            source=source,
            started_at=started_at,
            status=status,
            stop_requested=stop_requested,
            updated_at=updated_at,
        )

        return run
