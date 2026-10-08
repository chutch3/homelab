from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.source_inspection_input_transport import check_source_inspection_input_transport
from ..models.source_inspection_input_transport import SourceInspectionInputTransport
from ..types import UNSET, Unset
from typing import cast






T = TypeVar("T", bound="SourceInspectionInput")



@_attrs_define
class SourceInspectionInput:
    """ A link to one product page of a store, to find out how the store would be read.

        Attributes:
            url (str):
            transport (SourceInspectionInputTransport | Unset):  Default: 'direct'.
     """

    url: str
    transport: SourceInspectionInputTransport | Unset = 'direct'





    def to_dict(self) -> dict[str, Any]:
        url = self.url

        transport: str | Unset = UNSET
        if not isinstance(self.transport, Unset):
            transport = self.transport



        field_dict: dict[str, Any] = {}

        field_dict.update({
            "url": url,
        })
        if transport is not UNSET:
            field_dict["transport"] = transport

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        url = d.pop("url")

        _transport = d.pop("transport", UNSET)
        transport: SourceInspectionInputTransport | Unset
        if isinstance(_transport,  Unset):
            transport = UNSET
        else:
            transport = check_source_inspection_input_transport(_transport)




        source_inspection_input = cls(
            url=url,
            transport=transport,
        )

        return source_inspection_input
