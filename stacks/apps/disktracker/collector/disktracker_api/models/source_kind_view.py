from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.setting_group_view import SettingGroupView
  from ..models.setting_view import SettingView





T = TypeVar("T", bound="SourceKindView")



@_attrs_define
class SourceKindView:
    """
        Attributes:
            collected (bool):
            groups (list[SettingGroupView]):
            kind (str):
            label (str):
            page_test (bool):
            settings (list[SettingView]):
     """

    collected: bool
    groups: list[SettingGroupView]
    kind: str
    label: str
    page_test: bool
    settings: list[SettingView]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.setting_group_view import SettingGroupView # noqa: PLC0415
        from ..models.setting_view import SettingView # noqa: PLC0415
        collected = self.collected

        groups = []
        for groups_item_data in self.groups:
            groups_item = groups_item_data.to_dict()
            groups.append(groups_item)



        kind = self.kind

        label = self.label

        page_test = self.page_test

        settings = []
        for settings_item_data in self.settings:
            settings_item = settings_item_data.to_dict()
            settings.append(settings_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "collected": collected,
            "groups": groups,
            "kind": kind,
            "label": label,
            "page_test": page_test,
            "settings": settings,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.setting_group_view import SettingGroupView # noqa: PLC0415
        from ..models.setting_view import SettingView # noqa: PLC0415
        d = dict(src_dict)
        collected = d.pop("collected")

        groups = []
        _groups = d.pop("groups")
        for groups_item_data in (_groups):
            groups_item = SettingGroupView.from_dict(groups_item_data)



            groups.append(groups_item)


        kind = d.pop("kind")

        label = d.pop("label")

        page_test = d.pop("page_test")

        settings = []
        _settings = d.pop("settings")
        for settings_item_data in (_settings):
            settings_item = SettingView.from_dict(settings_item_data)



            settings.append(settings_item)


        source_kind_view = cls(
            collected=collected,
            groups=groups,
            kind=kind,
            label=label,
            page_test=page_test,
            settings=settings,
        )


        source_kind_view.additional_properties = d
        return source_kind_view

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
