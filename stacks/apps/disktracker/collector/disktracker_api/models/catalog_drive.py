from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.catalog_drive_issues_item import CatalogDriveIssuesItem
from ..models.catalog_drive_issues_item import check_catalog_drive_issues_item
from typing import cast

if TYPE_CHECKING:
  from ..models.drive import Drive





T = TypeVar("T", bound="CatalogDrive")



@_attrs_define
class CatalogDrive:
    """ A drive to manage: named by the title of the offer it is shown by (its cheapest in stock,
    else its cheapest), with how many offers it has and what it needs.

        Attributes:
            drive (Drive):
            issues (list[CatalogDriveIssuesItem]):
            offers (int):
            title (str):
     """

    drive: Drive
    issues: list[CatalogDriveIssuesItem]
    offers: int
    title: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.drive import Drive # noqa: PLC0415
        drive = self.drive.to_dict()

        issues = []
        for issues_item_data in self.issues:
            issues_item: str = issues_item_data
            issues.append(issues_item)



        offers = self.offers

        title = self.title


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "drive": drive,
            "issues": issues,
            "offers": offers,
            "title": title,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.drive import Drive # noqa: PLC0415
        d = dict(src_dict)
        drive = Drive.from_dict(d.pop("drive"))




        issues = []
        _issues = d.pop("issues")
        for issues_item_data in (_issues):
            issues_item = check_catalog_drive_issues_item(issues_item_data)



            issues.append(issues_item)


        offers = d.pop("offers")

        title = d.pop("title")

        catalog_drive = cls(
            drive=drive,
            issues=issues,
            offers=offers,
            title=title,
        )


        catalog_drive.additional_properties = d
        return catalog_drive

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
