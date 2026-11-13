from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.run_update_status import check_run_update_status
from ..models.run_update_status import RunUpdateStatus
from ..types import UNSET, Unset
from typing import cast
import datetime






T = TypeVar("T", bound="RunUpdate")



@_attrs_define
class RunUpdate:
    """ How far a run has got, or how it ended: running with its counts so far, or completed,
    failed or stopped (asked to stop) with when it finished. Counts are what it has done in all,
    not since it last said.

        Attributes:
            failed (int):
            ignored (int):
            queued (int):
            recorded (int):
            seen (int):
            finished_at (datetime.datetime | None | Unset): Required for completed, failed or stopped runs; must be omitted
                or null while running.
            reason (None | str | Unset): What went wrong, as the person running the collector would want to read it; only
                for a failed run.
            recheck_failed (int | Unset):  Default: 0.
            rechecked (int | Unset):  Default: 0.
            status (RunUpdateStatus | Unset):  Default: 'running'.
     """

    failed: int
    ignored: int
    queued: int
    recorded: int
    seen: int
    finished_at: datetime.datetime | None | Unset = UNSET
    reason: None | str | Unset = UNSET
    recheck_failed: int | Unset = 0
    rechecked: int | Unset = 0
    status: RunUpdateStatus | Unset = 'running'





    def to_dict(self) -> dict[str, Any]:
        failed = self.failed

        ignored = self.ignored

        queued = self.queued

        recorded = self.recorded

        seen = self.seen

        finished_at: None | str | Unset
        if isinstance(self.finished_at, Unset):
            finished_at = UNSET
        elif isinstance(self.finished_at, datetime.datetime):
            finished_at = self.finished_at.isoformat()
        else:
            finished_at = self.finished_at

        reason: None | str | Unset
        if isinstance(self.reason, Unset):
            reason = UNSET
        else:
            reason = self.reason

        recheck_failed = self.recheck_failed

        rechecked = self.rechecked

        status: str | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status



        field_dict: dict[str, Any] = {}

        field_dict.update({
            "failed": failed,
            "ignored": ignored,
            "queued": queued,
            "recorded": recorded,
            "seen": seen,
        })
        if finished_at is not UNSET:
            field_dict["finished_at"] = finished_at
        if reason is not UNSET:
            field_dict["reason"] = reason
        if recheck_failed is not UNSET:
            field_dict["recheck_failed"] = recheck_failed
        if rechecked is not UNSET:
            field_dict["rechecked"] = rechecked
        if status is not UNSET:
            field_dict["status"] = status

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        failed = d.pop("failed")

        ignored = d.pop("ignored")

        queued = d.pop("queued")

        recorded = d.pop("recorded")

        seen = d.pop("seen")

        def _parse_finished_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                finished_at_type_0 = datetime.datetime.fromisoformat(data)



                return finished_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        finished_at = _parse_finished_at(d.pop("finished_at", UNSET))


        def _parse_reason(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        reason = _parse_reason(d.pop("reason", UNSET))


        recheck_failed = d.pop("recheck_failed", UNSET)

        rechecked = d.pop("rechecked", UNSET)

        _status = d.pop("status", UNSET)
        status: RunUpdateStatus | Unset
        if isinstance(_status,  Unset):
            status = UNSET
        else:
            status = check_run_update_status(_status)




        run_update = cls(
            failed=failed,
            ignored=ignored,
            queued=queued,
            recorded=recorded,
            seen=seen,
            finished_at=finished_at,
            reason=reason,
            recheck_failed=recheck_failed,
            rechecked=rechecked,
            status=status,
        )

        return run_update
