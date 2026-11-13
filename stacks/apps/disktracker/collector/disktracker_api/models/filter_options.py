from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.choice_literalnew_manufacturer_recertified_refurbished_used import ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsed
  from ..models.choiceint import Choiceint
  from ..models.choicestr import Choicestr





T = TypeVar("T", bound="FilterOptions")



@_attrs_define
class FilterOptions:
    """ What the filters can choose from: every option the catalogue has, each with how many drives
    choosing it would give, with the search and every other filter as asked but not its own
    group's, whichever page is shown.

        Attributes:
            brands (list[Choicestr]):
            capacities (list[Choiceint]):
            conditions (list[ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsed]):
     """

    brands: list[Choicestr]
    capacities: list[Choiceint]
    conditions: list[ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsed]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.choice_literalnew_manufacturer_recertified_refurbished_used import ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsed # noqa: PLC0415
        from ..models.choiceint import Choiceint # noqa: PLC0415
        from ..models.choicestr import Choicestr # noqa: PLC0415
        brands = []
        for brands_item_data in self.brands:
            brands_item = brands_item_data.to_dict()
            brands.append(brands_item)



        capacities = []
        for capacities_item_data in self.capacities:
            capacities_item = capacities_item_data.to_dict()
            capacities.append(capacities_item)



        conditions = []
        for conditions_item_data in self.conditions:
            conditions_item = conditions_item_data.to_dict()
            conditions.append(conditions_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "brands": brands,
            "capacities": capacities,
            "conditions": conditions,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.choice_literalnew_manufacturer_recertified_refurbished_used import ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsed # noqa: PLC0415
        from ..models.choiceint import Choiceint # noqa: PLC0415
        from ..models.choicestr import Choicestr # noqa: PLC0415
        d = dict(src_dict)
        brands = []
        _brands = d.pop("brands")
        for brands_item_data in (_brands):
            brands_item = Choicestr.from_dict(brands_item_data)



            brands.append(brands_item)


        capacities = []
        _capacities = d.pop("capacities")
        for capacities_item_data in (_capacities):
            capacities_item = Choiceint.from_dict(capacities_item_data)



            capacities.append(capacities_item)


        conditions = []
        _conditions = d.pop("conditions")
        for conditions_item_data in (_conditions):
            conditions_item = ChoiceLiteralnewManufacturerRecertifiedRefurbishedUsed.from_dict(conditions_item_data)



            conditions.append(conditions_item)


        filter_options = cls(
            brands=brands,
            capacities=capacities,
            conditions=conditions,
        )


        filter_options.additional_properties = d
        return filter_options

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
