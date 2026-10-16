from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.shopify_source_input_basis import check_shopify_source_input_basis
from ..models.shopify_source_input_basis import ShopifySourceInputBasis
from ..models.shopify_source_input_transport import check_shopify_source_input_transport
from ..models.shopify_source_input_transport import ShopifySourceInputTransport
from ..types import UNSET, Unset
from typing import cast
from typing import Literal, cast

if TYPE_CHECKING:
  from ..models.shopify_settings_input import ShopifySettingsInput





T = TypeVar("T", bound="ShopifySourceInput")



@_attrs_define
class ShopifySourceInput:
    """
        Attributes:
            base_url (str): Store HTTP(S) base URL.
            kind (Literal['shopify']):
            name (str):
            settings (ShopifySettingsInput):
            basis (ShopifySourceInputBasis | Unset):  Default: 'unconfirmed'.
            enabled (bool | Unset):  Default: True.
            notes (str | Unset):  Default: ''.
            obey_robots (bool | Unset): False lets the collector read pages robots.txt disallows; only with basis
                permission. Default: True.
            schedule (str | Unset): Five-field cron schedule evaluated in UTC; default runs every eight hours. Default: '0
                */8 * * *'.
            transport (ShopifySourceInputTransport | Unset):  Default: 'direct'.
     """

    base_url: str
    kind: Literal['shopify']
    name: str
    settings: ShopifySettingsInput
    basis: ShopifySourceInputBasis | Unset = 'unconfirmed'
    enabled: bool | Unset = True
    notes: str | Unset = ''
    obey_robots: bool | Unset = True
    schedule: str | Unset = '0 */8 * * *'
    transport: ShopifySourceInputTransport | Unset = 'direct'





    def to_dict(self) -> dict[str, Any]:
        from ..models.shopify_settings_input import ShopifySettingsInput # noqa: PLC0415
        base_url = self.base_url

        kind = self.kind

        name = self.name

        settings = self.settings.to_dict()

        basis: str | Unset = UNSET
        if not isinstance(self.basis, Unset):
            basis = self.basis


        enabled = self.enabled

        notes = self.notes

        obey_robots = self.obey_robots

        schedule = self.schedule

        transport: str | Unset = UNSET
        if not isinstance(self.transport, Unset):
            transport = self.transport



        field_dict: dict[str, Any] = {}

        field_dict.update({
            "base_url": base_url,
            "kind": kind,
            "name": name,
            "settings": settings,
        })
        if basis is not UNSET:
            field_dict["basis"] = basis
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if notes is not UNSET:
            field_dict["notes"] = notes
        if obey_robots is not UNSET:
            field_dict["obey_robots"] = obey_robots
        if schedule is not UNSET:
            field_dict["schedule"] = schedule
        if transport is not UNSET:
            field_dict["transport"] = transport

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.shopify_settings_input import ShopifySettingsInput # noqa: PLC0415
        d = dict(src_dict)
        base_url = d.pop("base_url")

        kind = cast(Literal['shopify'] , d.pop("kind"))
        if kind != 'shopify':
            raise ValueError(f"kind must match const 'shopify', got '{kind}'")

        name = d.pop("name")

        settings = ShopifySettingsInput.from_dict(d.pop("settings"))




        _basis = d.pop("basis", UNSET)
        basis: ShopifySourceInputBasis | Unset
        if isinstance(_basis,  Unset):
            basis = UNSET
        else:
            basis = check_shopify_source_input_basis(_basis)




        enabled = d.pop("enabled", UNSET)

        notes = d.pop("notes", UNSET)

        obey_robots = d.pop("obey_robots", UNSET)

        schedule = d.pop("schedule", UNSET)

        _transport = d.pop("transport", UNSET)
        transport: ShopifySourceInputTransport | Unset
        if isinstance(_transport,  Unset):
            transport = UNSET
        else:
            transport = check_shopify_source_input_transport(_transport)




        shopify_source_input = cls(
            base_url=base_url,
            kind=kind,
            name=name,
            settings=settings,
            basis=basis,
            enabled=enabled,
            notes=notes,
            obey_robots=obey_robots,
            schedule=schedule,
            transport=transport,
        )

        return shopify_source_input
