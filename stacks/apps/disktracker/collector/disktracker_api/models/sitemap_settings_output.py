from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset







T = TypeVar("T", bound="SitemapSettingsOutput")



@_attrs_define
class SitemapSettingsOutput:
    """
        Attributes:
            data_brand_field (str):  Default: ''.
            data_in_stock_value (str):  Default: ''.
            data_items (str):  Default: ''.
            data_model_field (str):  Default: ''.
            data_name_field (str):  Default: ''.
            data_pattern (str):  Default: ''.
            data_price_field (str):  Default: ''.
            data_stock_field (str):  Default: ''.
            free_shipping_marker (str):  Default: ''.
            product_path_pattern (str):  Default: ''.
            sitemap_path (str):  Default: ''.
     """

    data_brand_field: str = ''
    data_in_stock_value: str = ''
    data_items: str = ''
    data_model_field: str = ''
    data_name_field: str = ''
    data_pattern: str = ''
    data_price_field: str = ''
    data_stock_field: str = ''
    free_shipping_marker: str = ''
    product_path_pattern: str = ''
    sitemap_path: str = ''





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
            "data_brand_field": data_brand_field,
            "data_in_stock_value": data_in_stock_value,
            "data_items": data_items,
            "data_model_field": data_model_field,
            "data_name_field": data_name_field,
            "data_pattern": data_pattern,
            "data_price_field": data_price_field,
            "data_stock_field": data_stock_field,
            "free_shipping_marker": free_shipping_marker,
            "product_path_pattern": product_path_pattern,
            "sitemap_path": sitemap_path,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        data_brand_field = d.pop("data_brand_field")

        data_in_stock_value = d.pop("data_in_stock_value")

        data_items = d.pop("data_items")

        data_model_field = d.pop("data_model_field")

        data_name_field = d.pop("data_name_field")

        data_pattern = d.pop("data_pattern")

        data_price_field = d.pop("data_price_field")

        data_stock_field = d.pop("data_stock_field")

        free_shipping_marker = d.pop("free_shipping_marker")

        product_path_pattern = d.pop("product_path_pattern")

        sitemap_path = d.pop("sitemap_path")

        sitemap_settings_output = cls(
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

        return sitemap_settings_output
