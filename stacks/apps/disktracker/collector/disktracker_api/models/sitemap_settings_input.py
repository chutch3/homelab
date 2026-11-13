from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset






T = TypeVar("T", bound="SitemapSettingsInput")



@_attrs_define
class SitemapSettingsInput:
    """
        Attributes:
            data_brand_field (str | Unset):  Default: ''.
            data_in_stock_value (str | Unset):  Default: ''.
            data_items (str | Unset):  Default: ''.
            data_model_field (str | Unset):  Default: ''.
            data_name_field (str | Unset):  Default: ''.
            data_pattern (str | Unset):  Default: ''.
            data_price_field (str | Unset):  Default: ''.
            data_stock_field (str | Unset):  Default: ''.
            free_shipping_marker (str | Unset):  Default: ''.
            product_path_pattern (str | Unset):  Default: ''.
            sitemap_path (str | Unset):  Default: ''.
     """

    data_brand_field: str | Unset = ''
    data_in_stock_value: str | Unset = ''
    data_items: str | Unset = ''
    data_model_field: str | Unset = ''
    data_name_field: str | Unset = ''
    data_pattern: str | Unset = ''
    data_price_field: str | Unset = ''
    data_stock_field: str | Unset = ''
    free_shipping_marker: str | Unset = ''
    product_path_pattern: str | Unset = ''
    sitemap_path: str | Unset = ''





    def to_dict(self) -> dict[str, Any]:
        data_brand_field = self.data_brand_field

        data_in_stock_value = self.data_in_stock_value

        data_items = self.data_items

        data_model_field = self.data_model_field

        data_name_field = self.data_name_field

        data_pattern = self.data_pattern

        data_price_field = self.data_price_field

        data_stock_field = self.data_stock_field

        free_shipping_marker = self.free_shipping_marker

        product_path_pattern = self.product_path_pattern

        sitemap_path = self.sitemap_path


        field_dict: dict[str, Any] = {}

        field_dict.update({
        })
        if data_brand_field is not UNSET:
            field_dict["data_brand_field"] = data_brand_field
        if data_in_stock_value is not UNSET:
            field_dict["data_in_stock_value"] = data_in_stock_value
        if data_items is not UNSET:
            field_dict["data_items"] = data_items
        if data_model_field is not UNSET:
            field_dict["data_model_field"] = data_model_field
        if data_name_field is not UNSET:
            field_dict["data_name_field"] = data_name_field
        if data_pattern is not UNSET:
            field_dict["data_pattern"] = data_pattern
        if data_price_field is not UNSET:
            field_dict["data_price_field"] = data_price_field
        if data_stock_field is not UNSET:
            field_dict["data_stock_field"] = data_stock_field
        if free_shipping_marker is not UNSET:
            field_dict["free_shipping_marker"] = free_shipping_marker
        if product_path_pattern is not UNSET:
            field_dict["product_path_pattern"] = product_path_pattern
        if sitemap_path is not UNSET:
            field_dict["sitemap_path"] = sitemap_path

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        data_brand_field = d.pop("data_brand_field", UNSET)

        data_in_stock_value = d.pop("data_in_stock_value", UNSET)

        data_items = d.pop("data_items", UNSET)

        data_model_field = d.pop("data_model_field", UNSET)

        data_name_field = d.pop("data_name_field", UNSET)

        data_pattern = d.pop("data_pattern", UNSET)

        data_price_field = d.pop("data_price_field", UNSET)

        data_stock_field = d.pop("data_stock_field", UNSET)

        free_shipping_marker = d.pop("free_shipping_marker", UNSET)

        product_path_pattern = d.pop("product_path_pattern", UNSET)

        sitemap_path = d.pop("sitemap_path", UNSET)

        sitemap_settings_input = cls(
            data_brand_field=data_brand_field,
            data_in_stock_value=data_in_stock_value,
            data_items=data_items,
            data_model_field=data_model_field,
            data_name_field=data_name_field,
            data_pattern=data_pattern,
            data_price_field=data_price_field,
            data_stock_field=data_stock_field,
            free_shipping_marker=free_shipping_marker,
            product_path_pattern=product_path_pattern,
            sitemap_path=sitemap_path,
        )

        return sitemap_settings_input
