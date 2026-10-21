"""What a price submission is taken to say: the price it observed, and what binds its save key to
it. Recording it is tested against the database (tests/integration)."""

from typing import Any

import pytest

from disktracker.catalog.price_service import fingerprint, observation
from disktracker.catalog.schemas import PriceInput


def a_price(**fields: Any) -> PriceInput:
    """A price a person enters for a drive at a store."""
    return PriceInput.model_validate(
        {
            "drive_id": "22222222-2222-4222-8222-222222222222",
            "store": "serverpartdeals",
            "condition": "new",
            "item_price_cents": 1_000_000,
            "shipping_cents": 500,
            **fields,
        }
    )


def a_recheck(**fields: Any) -> PriceInput:
    """A collector's price of an offer it names, as its page shows it now."""
    return PriceInput.model_validate(
        {
            "offer_id": "11111111-1111-4111-8111-111111111111",
            "provenance": "collected",
            "item_price_cents": 1_000_000,
            "shipping_cents": 500,
            **fields,
        }
    )


def test_a_collected_sold_out_price_is_only_a_stock_state() -> None:
    """Whatever a store shows while sold out (a placeholder, say) is not a price."""
    price = observation(a_recheck(in_stock=False), collected=True)

    assert (price["item_price_cents"], price["shipping_cents"], price["in_stock"]) == (
        None, None, False,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("entry", "collected"),
    [(a_price(in_stock=False), False), (a_recheck(in_stock=True), True)],
    ids=["entered sold out", "collected in stock"],
)
def test_any_other_price_is_recorded_as_given(entry: PriceInput, collected: bool) -> None:
    price = observation(entry, collected)

    assert (price["item_price_cents"], price["shipping_cents"]) == (1_000_000, 500)


def test_a_save_key_is_bound_to_what_was_sent_under_it_and_where() -> None:
    sent = [
        fingerprint("price", a_price()),
        fingerprint("price", a_price()),
        fingerprint("price", a_price(item_price_cents=999)),
        fingerprint("ingestion", a_price()),
    ]

    assert sent[0] == sent[1] != sent[2]
    assert sent[3] != sent[0]
