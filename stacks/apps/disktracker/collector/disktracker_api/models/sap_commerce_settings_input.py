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
            api_url (str | Unset):  Default: ''.
            product_path_pattern (str | Unset):  Default: ''.
            recertified_sku_prefix (str | Unset):  Default: ''.
            site (str | Unset):  Default: ''.
            sitemap_path (str | Unset):  Default: ''.
     """

    api_url: str | Unset = ''
    product_path_pattern: str | Unset = ''
    recertified_sku_prefix: str | Unset = ''
    site: str | Unset = ''
    sitemap_path: str | Unset = ''





    def to_dict(self) -> dict[str, Any]:
        api_url = self.api_url

        product_path_pattern = self.product_path_pattern

        recertified_sku_prefix = self.recertified_sku_prefix

        site = self.site

        sitemap_path = self.sitemap_path


        field_dict: dict[str, Any] = {}

        field_dict.update({
        })
        if api_url is not UNSET:
            field_dict["api_url"] = api_url
        if product_path_pattern is not UNSET:
            field_dict["product_path_pattern"] = product_path_pattern
        if recertified_sku_prefix is not UNSET:
            field_dict["recertified_sku_prefix"] = recertified_sku_prefix
        if site is not UNSET:
            field_dict["site"] = site
        if sitemap_path is not UNSET:
            field_dict["sitemap_path"] = sitemap_path

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        api_url = d.pop("api_url", UNSET)

        product_path_pattern = d.pop("product_path_pattern", UNSET)

        recertified_sku_prefix = d.pop("recertified_sku_prefix", UNSET)

        site = d.pop("site", UNSET)

        sitemap_path = d.pop("sitemap_path", UNSET)

        sap_commerce_settings_input = cls(
            api_url=api_url,
            product_path_pattern=product_path_pattern,
            recertified_sku_prefix=recertified_sku_prefix,
            site=site,
            sitemap_path=sitemap_path,
        )

        return sap_commerce_settings_input
