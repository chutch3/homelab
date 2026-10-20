"""What a price submission is taken to say: the price it observed, and what binds its save key to
it. Recording it is tested against the database (tests/integration)."""

from typing import Any

import pytest

from disktracker.catalog.price_service import fingerprint, observation
from disktracker.catalog.schemas import PriceInput


def a_price(**fields: Any) -> PriceInput:
    return PriceInput.model_validate(
        {
            "store": "serverpartdeals",
            "mpn": "ST18000NM000J",
            "condition": "new",
            "title": "Exos X18",
            "url": "https://www.serverpartdeals.com/products/x18",
            "item_price_cents": 1_000_000,
            "shipping_cents": 500,
            **fields,
        }
    )


def test_a_collected_sold_out_price_is_only_a_stock_state() -> None:
    """Whatever a store shows while sold out (a placeholder, say) is not a price."""
    price = observation(a_price(provenance="collected", in_stock=False))

    assert (price["item_price_cents"], price["shipping_cents"], price["in_stock"]) == (
        None, None, False,
    )  # fmt: skip


@pytest.mark.parametrize(
    "entry",
    [{"provenance": "manual", "in_stock": False}, {"provenance": "collected", "in_stock": True}],
    ids=["entered sold out", "collected in stock"],
)
def test_any_other_price_is_recorded_as_given(entry: dict[str, Any]) -> None:
    price = observation(a_price(**entry))

    assert (price["item_price_cents"], price["shipping_cents"]) == (1_000_000, 500)


def test_a_save_key_is_bound_to_what_was_sent_under_it() -> None:
    sent = [
        fingerprint(a_price()),
        fingerprint(a_price()),
        fingerprint(a_price(item_price_cents=999)),
    ]

    assert sent[0] == sent[1] != sent[2]
