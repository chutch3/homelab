from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from uuid import UUID
import datetime






T = TypeVar("T", bound="RunStart")



@_attrs_define
class RunStart:
    """ A run as it starts. id: chosen by the collector, so a start whose answer was lost can be
    sent again.

        Attributes:
            id (UUID):
            source (str): Stable source key from GET /api/sources, not its UUID.
            started_at (datetime.datetime):
     """

    id: UUID
    source: str
    started_at: datetime.datetime





    def to_dict(self) -> dict[str, Any]:
        id = str(self.id)

        source = self.source

        started_at = self.started_at.isoformat()


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "id": id,
            "source": source,
            "started_at": started_at,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = UUID(d.pop("id"))




        source = d.pop("source")

        started_at = datetime.datetime.fromisoformat(d.pop("started_at"))




        run_start = cls(
            id=id,
            source=source,
            started_at=started_at,
        )

        return run_start
