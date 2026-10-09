from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.setting_view_type import check_setting_view_type
from ..models.setting_view_type import SettingViewType
from typing import cast






T = TypeVar("T", bound="SettingView")



@_attrs_define
class SettingView:
    """ One thing a kind of store needs to know: how the form asks for it, and how it is
    checked (disktracker.kinds).

        Attributes:
            capturing (bool):
            description (str):
            group (str):
            label (str):
            name (str):
            needs (str):
            pattern (str):
            pattern_message (str):
            placeholder (str):
            regex (bool):
            required (bool):
            type_ (SettingViewType):
     """

    capturing: bool
    description: str
    group: str
    label: str
    name: str
    needs: str
    pattern: str
    pattern_message: str
    placeholder: str
    regex: bool
    required: bool
    type_: SettingViewType
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        capturing = self.capturing

        description = self.description

        group = self.group

        label = self.label

        name = self.name

        needs = self.needs

        pattern = self.pattern

        pattern_message = self.pattern_message

        placeholder = self.placeholder

        regex = self.regex

        required = self.required

        type_: str = self.type_


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "capturing": capturing,
            "description": description,
            "group": group,
            "label": label,
            "name": name,
            "needs": needs,
            "pattern": pattern,
            "pattern_message": pattern_message,
            "placeholder": placeholder,
            "regex": regex,
            "required": required,
            "type": type_,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        capturing = d.pop("capturing")

        description = d.pop("description")

        group = d.pop("group")

        label = d.pop("label")

        name = d.pop("name")

        needs = d.pop("needs")

        pattern = d.pop("pattern")

        pattern_message = d.pop("pattern_message")

        placeholder = d.pop("placeholder")

        regex = d.pop("regex")

        required = d.pop("required")

        type_ = check_setting_view_type(d.pop("type"))




        setting_view = cls(
            capturing=capturing,
            description=description,
            group=group,
            label=label,
            name=name,
            needs=needs,
            pattern=pattern,
            pattern_message=pattern_message,
            placeholder=placeholder,
            regex=regex,
            required=required,
            type_=type_,
        )


        setting_view.additional_properties = d
        return setting_view

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
