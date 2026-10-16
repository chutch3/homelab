from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset







T = TypeVar("T", bound="SapCommerceSettingsOutput")



@_attrs_define
class SapCommerceSettingsOutput:
    """
        Attributes:
            api_url (str):  Default: ''.
            product_path_pattern (str):  Default: ''.
            recertified_sku_prefix (str):  Default: ''.
            site (str):  Default: ''.
            sitemap_path (str):  Default: ''.
     """

    api_url: str = ''
    product_path_pattern: str = ''
    recertified_sku_prefix: str = ''
    site: str = ''
    sitemap_path: str = ''





    def to_dict(self) -> dict[str, Any]:
        api_url = self.api_url

        product_path_pattern = self.product_path_pattern

        recertified_sku_prefix = self.recertified_sku_prefix

        site = self.site

        sitemap_path = self.sitemap_path


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "api_url": api_url,
            "product_path_pattern": product_path_pattern,
            "recertified_sku_prefix": recertified_sku_prefix,
            "site": site,
            "sitemap_path": sitemap_path,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        api_url = d.pop("api_url")

        product_path_pattern = d.pop("product_path_pattern")

        recertified_sku_prefix = d.pop("recertified_sku_prefix")

        site = d.pop("site")

        sitemap_path = d.pop("sitemap_path")

        sap_commerce_settings_output = cls(
            api_url=api_url,
            product_path_pattern=product_path_pattern,
            recertified_sku_prefix=recertified_sku_prefix,
            site=site,
            sitemap_path=sitemap_path,
        )

        return sap_commerce_settings_output
