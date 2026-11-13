from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from uuid import UUID






T = TypeVar("T", bound="Heartbeat")



@_attrs_define
class Heartbeat:
    """ A collector saying it is alive, with the runs it has: none when it has nothing to do. Any
    other run still marked running is abandoned.

        Attributes:
            runs (list[UUID] | Unset): All runs currently owned by the worker. Any other running run is abandoned; send an
                empty list while idle.
     """

    runs: list[UUID] | Unset = UNSET





    def to_dict(self) -> dict[str, Any]:
        runs: list[str] | Unset = UNSET
        if not isinstance(self.runs, Unset):
            runs = []
            for runs_item_data in self.runs:
                runs_item = str(runs_item_data)
                runs.append(runs_item)




        field_dict: dict[str, Any] = {}

        field_dict.update({
        })
        if runs is not UNSET:
            field_dict["runs"] = runs

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _runs = d.pop("runs", UNSET)
        runs: list[UUID] | Unset = UNSET
        if _runs is not UNSET:
            runs = []
            for runs_item_data in _runs:
                runs_item = UUID(runs_item_data)



                runs.append(runs_item)


        heartbeat = cls(
            runs=runs,
        )

        return heartbeat
