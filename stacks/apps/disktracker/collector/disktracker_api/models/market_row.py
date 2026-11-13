from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.condition_prices import ConditionPrices
  from ..models.drive import Drive
  from ..models.offer_summary import OfferSummary
  from ..models.price_range import PriceRange





T = TypeVar("T", bound="MarketRow")



@_attrs_define
class MarketRow:
    """ A drive as the market shows it: by its cheapest matching offer in stock (else its cheapest
    matching offer), with how many stores and sellers offer it and what each condition it is
    offered in costs, among the offers that match, and the range of its price in the condition of
    the offer it is shown by.

        Attributes:
            conditions (list[ConditionPrices]):
            drive (Drive):
            offer (OfferSummary): An offer with its latest price; what a table of offers needs.
            range_ (None | PriceRange):
            stores (int):
     """

    conditions: list[ConditionPrices]
    drive: Drive
    offer: OfferSummary
    range_: None | PriceRange
    stores: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.condition_prices import ConditionPrices # noqa: PLC0415
        from ..models.drive import Drive # noqa: PLC0415
        from ..models.offer_summary import OfferSummary # noqa: PLC0415
        from ..models.price_range import PriceRange # noqa: PLC0415
        conditions = []
        for conditions_item_data in self.conditions:
            conditions_item = conditions_item_data.to_dict()
            conditions.append(conditions_item)



        drive = self.drive.to_dict()

        offer = self.offer.to_dict()

        range_: dict[str, Any] | None
        if isinstance(self.range_, PriceRange):
            range_ = self.range_.to_dict()
        else:
            range_ = self.range_

        stores = self.stores


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "conditions": conditions,
            "drive": drive,
            "offer": offer,
            "range": range_,
            "stores": stores,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.condition_prices import ConditionPrices # noqa: PLC0415
        from ..models.drive import Drive # noqa: PLC0415
        from ..models.offer_summary import OfferSummary # noqa: PLC0415
        from ..models.price_range import PriceRange # noqa: PLC0415
        d = dict(src_dict)
        conditions = []
        _conditions = d.pop("conditions")
        for conditions_item_data in (_conditions):
            conditions_item = ConditionPrices.from_dict(conditions_item_data)



            conditions.append(conditions_item)


        drive = Drive.from_dict(d.pop("drive"))




        offer = OfferSummary.from_dict(d.pop("offer"))




        def _parse_range_(data: object) -> None | PriceRange:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                range_type_0 = PriceRange.from_dict(data)



                return range_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | PriceRange, data)

        range_ = _parse_range_(d.pop("range"))


        stores = d.pop("stores")

        market_row = cls(
            conditions=conditions,
            drive=drive,
            offer=offer,
            range_=range_,
            stores=stores,
        )


        market_row.additional_properties = d
        return market_row

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
