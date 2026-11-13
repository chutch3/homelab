from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset






T = TypeVar("T", bound="SapCommerceSettingsInput")



@_attrs_define
class SapCommerceSettingsInput:
    """
        Attributes:
            api_url (str):
            site (str):
            product_path_pattern (str | Unset):  Default: ''.
            recertified_sku_prefix (str | Unset):  Default: ''.
            sitemap_path (str | Unset):  Default: ''.
     """

    api_url: str
    site: str
    product_path_pattern: str | Unset = ''
    recertified_sku_prefix: str | Unset = ''
    sitemap_path: str | Unset = ''





    def to_dict(self) -> dict[str, Any]:
        api_url = self.api_url

        site = self.site

        product_path_pattern = self.product_path_pattern

        recertified_sku_prefix = self.recertified_sku_prefix

        sitemap_path = self.sitemap_path


        field_dict: dict[str, Any] = {}

        field_dict.update({
            "api_url": api_url,
            "site": site,
        })
        if product_path_pattern is not UNSET:
            field_dict["product_path_pattern"] = product_path_pattern
        if recertified_sku_prefix is not UNSET:
            field_dict["recertified_sku_prefix"] = recertified_sku_prefix
        if sitemap_path is not UNSET:
            field_dict["sitemap_path"] = sitemap_path

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        api_url = d.pop("api_url")

        site = d.pop("site")

        product_path_pattern = d.pop("product_path_pattern", UNSET)

        recertified_sku_prefix = d.pop("recertified_sku_prefix", UNSET)

        sitemap_path = d.pop("sitemap_path", UNSET)

        sap_commerce_settings_input = cls(
            api_url=api_url,
            site=site,
            product_path_pattern=product_path_pattern,
            recertified_sku_prefix=recertified_sku_prefix,
            sitemap_path=sitemap_path,
        )

        return sap_commerce_settings_input
