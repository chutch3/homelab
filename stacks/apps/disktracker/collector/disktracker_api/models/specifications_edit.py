from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.specifications_edit_form_factor import check_specifications_edit_form_factor
from ..models.specifications_edit_form_factor import SpecificationsEditFormFactor
from ..models.specifications_edit_intended_use_item import check_specifications_edit_intended_use_item
from ..models.specifications_edit_intended_use_item import SpecificationsEditIntendedUseItem
from ..models.specifications_edit_interface import check_specifications_edit_interface
from ..models.specifications_edit_interface import SpecificationsEditInterface
from ..models.specifications_edit_media_type import check_specifications_edit_media_type
from ..models.specifications_edit_media_type import SpecificationsEditMediaType
from ..models.specifications_edit_recording_type import check_specifications_edit_recording_type
from ..models.specifications_edit_recording_type import SpecificationsEditRecordingType
from ..types import UNSET, Unset
from typing import cast






T = TypeVar("T", bound="SpecificationsEdit")



@_attrs_define
class SpecificationsEdit:
    """ Specifications corrected by hand: each one given takes the place of the one kept, and
    each one left out stays. None can be cleared; unknown is a value like any other.

        Attributes:
            form_factor (SpecificationsEditFormFactor | Unset):  Default: 'unknown'.
            intended_use (list[SpecificationsEditIntendedUseItem] | Unset):
            interface (SpecificationsEditInterface | Unset):  Default: 'unknown'.
            media_type (SpecificationsEditMediaType | Unset):  Default: 'unknown'.
            recording_type (SpecificationsEditRecordingType | Unset):  Default: 'unknown'.
     """

    form_factor: SpecificationsEditFormFactor | Unset = 'unknown'
    intended_use: list[SpecificationsEditIntendedUseItem] | Unset = UNSET
    interface: SpecificationsEditInterface | Unset = 'unknown'
    media_type: SpecificationsEditMediaType | Unset = 'unknown'
    recording_type: SpecificationsEditRecordingType | Unset = 'unknown'





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
        form_factor: SpecificationsEditFormFactor | Unset
        if isinstance(_form_factor,  Unset):
            form_factor = UNSET
        else:
            form_factor = check_specifications_edit_form_factor(_form_factor)




        _intended_use = d.pop("intended_use", UNSET)
        intended_use: list[SpecificationsEditIntendedUseItem] | Unset = UNSET
        if _intended_use is not UNSET:
            intended_use = []
            for intended_use_item_data in _intended_use:
                intended_use_item = check_specifications_edit_intended_use_item(intended_use_item_data)



                intended_use.append(intended_use_item)


        _interface = d.pop("interface", UNSET)
        interface: SpecificationsEditInterface | Unset
        if isinstance(_interface,  Unset):
            interface = UNSET
        else:
            interface = check_specifications_edit_interface(_interface)




        _media_type = d.pop("media_type", UNSET)
        media_type: SpecificationsEditMediaType | Unset
        if isinstance(_media_type,  Unset):
            media_type = UNSET
        else:
            media_type = check_specifications_edit_media_type(_media_type)




        _recording_type = d.pop("recording_type", UNSET)
        recording_type: SpecificationsEditRecordingType | Unset
        if isinstance(_recording_type,  Unset):
            recording_type = UNSET
        else:
            recording_type = check_specifications_edit_recording_type(_recording_type)




        specifications_edit = cls(
            form_factor=form_factor,
            intended_use=intended_use,
            interface=interface,
            media_type=media_type,
            recording_type=recording_type,
        )

        return specifications_edit
