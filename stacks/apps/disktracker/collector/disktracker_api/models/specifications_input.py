from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.specifications_input_form_factor import check_specifications_input_form_factor
from ..models.specifications_input_form_factor import SpecificationsInputFormFactor
from ..models.specifications_input_intended_use_item import check_specifications_input_intended_use_item
from ..models.specifications_input_intended_use_item import SpecificationsInputIntendedUseItem
from ..models.specifications_input_interface import check_specifications_input_interface
from ..models.specifications_input_interface import SpecificationsInputInterface
from ..models.specifications_input_media_type import check_specifications_input_media_type
from ..models.specifications_input_media_type import SpecificationsInputMediaType
from ..models.specifications_input_recording_type import check_specifications_input_recording_type
from ..models.specifications_input_recording_type import SpecificationsInputRecordingType
from ..types import UNSET, Unset
from typing import cast






T = TypeVar("T", bound="SpecificationsInput")



@_attrs_define
class SpecificationsInput:
    """
        Attributes:
            form_factor (SpecificationsInputFormFactor | Unset):  Default: 'unknown'.
            intended_use (list[SpecificationsInputIntendedUseItem] | Unset):
            interface (SpecificationsInputInterface | Unset):  Default: 'unknown'.
            media_type (SpecificationsInputMediaType | Unset):  Default: 'unknown'.
            recording_type (SpecificationsInputRecordingType | Unset):  Default: 'unknown'.
     """

    form_factor: SpecificationsInputFormFactor | Unset = 'unknown'
    intended_use: list[SpecificationsInputIntendedUseItem] | Unset = UNSET
    interface: SpecificationsInputInterface | Unset = 'unknown'
    media_type: SpecificationsInputMediaType | Unset = 'unknown'
    recording_type: SpecificationsInputRecordingType | Unset = 'unknown'





    def to_dict(self) -> dict[str, Any]:
        form_factor: str | Unset = UNSET
        if not isinstance(self.form_factor, Unset):
            form_factor = self.form_factor


        intended_use: list[str] | Unset = UNSET
        if not isinstance(self.intended_use, Unset):
            intended_use = []
            for intended_use_item_data in self.intended_use:
                intended_use_item: str = intended_use_item_data
                intended_use.append(intended_use_item)



        interface: str | Unset = UNSET
        if not isinstance(self.interface, Unset):
            interface = self.interface


        media_type: str | Unset = UNSET
        if not isinstance(self.media_type, Unset):
            media_type = self.media_type


        recording_type: str | Unset = UNSET
        if not isinstance(self.recording_type, Unset):
            recording_type = self.recording_type



        field_dict: dict[str, Any] = {}

        field_dict.update({
        })
        if form_factor is not UNSET:
            field_dict["form_factor"] = form_factor
        if intended_use is not UNSET:
            field_dict["intended_use"] = intended_use
        if interface is not UNSET:
            field_dict["interface"] = interface
        if media_type is not UNSET:
            field_dict["media_type"] = media_type
        if recording_type is not UNSET:
            field_dict["recording_type"] = recording_type

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _form_factor = d.pop("form_factor", UNSET)
        form_factor: SpecificationsInputFormFactor | Unset
        if isinstance(_form_factor,  Unset):
            form_factor = UNSET
        else:
            form_factor = check_specifications_input_form_factor(_form_factor)




        _intended_use = d.pop("intended_use", UNSET)
        intended_use: list[SpecificationsInputIntendedUseItem] | Unset = UNSET
        if _intended_use is not UNSET:
            intended_use = []
            for intended_use_item_data in _intended_use:
                intended_use_item = check_specifications_input_intended_use_item(intended_use_item_data)



                intended_use.append(intended_use_item)


        _interface = d.pop("interface", UNSET)
        interface: SpecificationsInputInterface | Unset
        if isinstance(_interface,  Unset):
            interface = UNSET
        else:
            interface = check_specifications_input_interface(_interface)




        _media_type = d.pop("media_type", UNSET)
        media_type: SpecificationsInputMediaType | Unset
        if isinstance(_media_type,  Unset):
            media_type = UNSET
        else:
            media_type = check_specifications_input_media_type(_media_type)




        _recording_type = d.pop("recording_type", UNSET)
        recording_type: SpecificationsInputRecordingType | Unset
        if isinstance(_recording_type,  Unset):
            recording_type = UNSET
        else:
            recording_type = check_specifications_input_recording_type(_recording_type)




        specifications_input = cls(
            form_factor=form_factor,
            intended_use=intended_use,
            interface=interface,
            media_type=media_type,
            recording_type=recording_type,
        )

        return specifications_input
