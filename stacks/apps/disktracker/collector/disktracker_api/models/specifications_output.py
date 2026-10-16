from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.specifications_output_form_factor import check_specifications_output_form_factor
from ..models.specifications_output_form_factor import SpecificationsOutputFormFactor
from ..models.specifications_output_intended_use_item import check_specifications_output_intended_use_item
from ..models.specifications_output_intended_use_item import SpecificationsOutputIntendedUseItem
from ..models.specifications_output_interface import check_specifications_output_interface
from ..models.specifications_output_interface import SpecificationsOutputInterface
from ..models.specifications_output_media_type import check_specifications_output_media_type
from ..models.specifications_output_media_type import SpecificationsOutputMediaType
from ..models.specifications_output_recording_type import check_specifications_output_recording_type
from ..models.specifications_output_recording_type import SpecificationsOutputRecordingType
from typing import cast






T = TypeVar("T", bound="SpecificationsOutput")



@_attrs_define
class SpecificationsOutput:
    """
        Attributes:
            form_factor (SpecificationsOutputFormFactor):  Default: 'unknown'.
            intended_use (list[SpecificationsOutputIntendedUseItem]):
            interface (SpecificationsOutputInterface):  Default: 'unknown'.
            media_type (SpecificationsOutputMediaType):  Default: 'unknown'.
            recording_type (SpecificationsOutputRecordingType):  Default: 'unknown'.
     """

    intended_use: list[SpecificationsOutputIntendedUseItem]
    form_factor: SpecificationsOutputFormFactor = 'unknown'
    interface: SpecificationsOutputInterface = 'unknown'
    media_type: SpecificationsOutputMediaType = 'unknown'
    recording_type: SpecificationsOutputRecordingType = 'unknown'





    def to_dict(self) -> dict[str, Any]:
        form_factor: str = self.form_factor

        intended_use = []
        for intended_use_item_data in self.intended_use:
            intended_use_item: str = intended_use_item_data
            intended_use.append(intended_use_item)



        interface: str = self.interface

        media_type: str = self.media_type

        recording_type: str = self.recording_type


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "form_factor": form_factor,
            "intended_use": intended_use,
            "interface": interface,
            "media_type": media_type,
            "recording_type": recording_type,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        form_factor = check_specifications_output_form_factor(d.pop("form_factor"))




        intended_use = []
        _intended_use = d.pop("intended_use")
        for intended_use_item_data in (_intended_use):
            intended_use_item = check_specifications_output_intended_use_item(intended_use_item_data)



            intended_use.append(intended_use_item)


        interface = check_specifications_output_interface(d.pop("interface"))




        media_type = check_specifications_output_media_type(d.pop("media_type"))




        recording_type = check_specifications_output_recording_type(d.pop("recording_type"))




        specifications_output = cls(
            form_factor=form_factor,
            intended_use=intended_use,
            interface=interface,
            media_type=media_type,
            recording_type=recording_type,
        )

        return specifications_output
