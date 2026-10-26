from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from disktracker.catalog.schemas import (
    ConditionRule,
    DriveEdit,
    IngestionInput,
    ListingText,
    MatchDecision,
    PriceInput,
    ReviewDecision,
    Specifications,
)


def test_unknown_by_default() -> None:
    assert Specifications().model_dump() == {
        "media_type": "unknown",
        "form_factor": "unknown",
        "interface": "unknown",
        "recording_type": "unknown",
        "intended_use": [],
    }


def test_repeated_intended_uses_are_kept_once() -> None:
    specs = Specifications.model_validate({"intended_use": ["nas", "enterprise", "nas"]})
    assert specs.intended_use == ["nas", "enterprise"]


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"media_type": "floppy"}, "media_type"),
        ({"form_factor": "5_25"}, "form_factor"),
        ({"interface": "sata-express"}, "interface"),
        ({"recording_type": {"value": "cmr"}}, "recording_type"),
        ({"intended_use": ["unknown"]}, "intended_use"),
        ({"smr_management": "host_managed"}, "smr_management"),
    ],
)
def test_invalid_specifications_are_rejected(data: dict[str, object], field: str) -> None:
    with pytest.raises(ValidationError) as error:
        Specifications.model_validate(data)
    assert error.value.errors()[0]["loc"][0] == field


DRIVE = "22222222-2222-4222-8222-222222222222"


def a_price(**fields: Any) -> dict[str, Any]:
    """A price a person enters for a drive at a one-off store."""
    return {
        "drive_id": DRIVE,
        "store": "other",
        "seller": "Example seller",
        "condition": "manufacturer_recertified",
        "title": "Seagate Exos X18",
        "url": "https://example.com/disk",
        "item_price_cents": 18900,
        "shipping_cents": 1000,
        "observed_at": "2026-09-21T12:00:00Z",
        **fields,
    }


def a_page(**fields: Any) -> dict[str, Any]:
    """A store page as a collector read it."""
    return {
        "store": "serverpartdeals",
        "mpn": "ST18000NM000J",
        "condition": "manufacturer_recertified",
        "title": "Seagate Exos X18",
        "url": "https://www.serverpartdeals.com/products/x18",
        "capacity_gb": 18000,
        "item_price_cents": 18900,
        "shipping_cents": 1000,
        "observed_at": "2026-09-21T12:00:00Z",
        **fields,
    }


BUILT = {PriceInput: a_price, IngestionInput: a_page}


def refused(model: Any, data: Any) -> list[tuple[tuple[Any, ...], str]]:
    """Where each complaint about data is, and what it says."""
    with pytest.raises(ValidationError) as error:
        TypeAdapter(model).validate_python(data)
    return [(issue["loc"], issue["msg"]) for issue in error.value.errors()]


def test_a_price_left_without_shipping_notes_or_time_is_free_unnoted_and_seen_now() -> None:
    entered = a_price()
    for field in ("shipping_cents", "observed_at"):
        del entered[field]

    price = PriceInput.model_validate(entered)

    assert (price.shipping_cents, price.notes, price.observed_at) == (0, "", None)


@pytest.mark.parametrize(
    ("model", "field", "value"),
    [
        *[
            (model, field, value)
            for model in (PriceInput, IngestionInput)
            for field, value in [
                ("title", "   "),
                ("condition", "excellent"),
                # Only the four normalized conditions are accepted.
                ("condition", "open_box"),
                ("condition", "seller_refurbished"),
                ("condition", "unknown"),
                ("url", "javascript:alert(1)"),
                ("shipping_cents", -1),
                ("item_price_cents", 1.5),
                ("item_price_cents", None),
                ("observed_at", "2026-09-21T12:00:00"),
                # Fees are part of shipping, and availability is in_stock.
                ("fee_cents", 0),
                ("availability", "in_stock"),
            ]
        ],
        # What a page says of its drive.
        (IngestionInput, "mpn", ""),
        (IngestionInput, "capacity_gb", 0),
        (IngestionInput, "capacity_gb", 18000.5),
        (IngestionInput, "capacity_gb", "18 TB"),
    ],
)
def test_a_price_that_does_not_fit_is_refused_on_the_field_at_fault(
    model: type, field: str, value: object
) -> None:
    assert [loc for loc, _ in refused(model, BUILT[model](**{field: value}))] == [(field,)]


def test_a_price_needs_an_item_price() -> None:
    entered = a_price()
    del entered["item_price_cents"]

    assert refused(PriceInput, entered) == [
        (("item_price_cents",), "Value error, Enter the item price.")
    ]


@pytest.mark.parametrize(
    ("model", "entered"),
    [
        (PriceInput, a_price(item_price_cents=0)),
        # Sold out with a price of nothing is no better: there is no price to carry.
        (PriceInput, a_price(item_price_cents=0, in_stock=False)),
        (IngestionInput, a_page(item_price_cents=0)),
    ],
    ids=["entered", "entered sold out", "collected"],
)
def test_a_price_of_nothing_is_not_a_price_whoever_enters_it(
    model: type, entered: dict[str, Any]
) -> None:
    """A store writes 0 for a drive it sells only by quote; recorded, it would be the lowest
    price of everything."""
    assert refused(model, entered) == [
        (("item_price_cents",), "Value error, Enter a price above zero.")
    ]


def test_a_sold_out_price_may_leave_its_price_out() -> None:
    assert PriceInput.model_validate(a_price(item_price_cents=None, in_stock=False))


def test_a_page_may_leave_out_what_it_does_not_say_and_wait_for_review() -> None:
    page = IngestionInput.model_validate(a_page(mpn=None, condition=None, capacity_gb=None))

    assert (page.mpn, page.condition, page.capacity_gb) == (None, None, None)


def test_a_price_names_its_offer_or_its_drive_but_not_both() -> None:
    offer_id = str(uuid4())
    named = {"offer_id": offer_id, "item_price_cents": 17900}

    assert PriceInput.model_validate(named).offer_id == UUID(offer_id)
    assert PriceInput.model_validate(a_price()).drive_id == UUID(DRIVE)
    assert refused(PriceInput, a_price(offer_id=offer_id)) == [
        (("drive_id",), "Value error, Name the offer or its drive, not both."),
        (("store",), "Value error, Leave the store out when the offer is named."),
        (("condition",), "Value error, Leave this out when the offer is named."),
    ]
    assert refused(PriceInput, {"item_price_cents": 17900}) == [
        (("drive_id",), "Value error, Name the offer, or the drive it is of.")
    ]
    placed = {"drive_id": DRIVE, "item_price_cents": 17900}
    assert refused(PriceInput, placed) == [
        (("store",), "Value error, Choose a store."),
        (("condition",), "Value error, Choose its condition."),
    ]


@pytest.mark.parametrize("model", [PriceInput, IngestionInput])
def test_a_price_at_a_one_off_store_names_its_seller(
    model: type[PriceInput] | type[IngestionInput],
) -> None:
    built = BUILT[model]
    assert refused(model, built(store="other", seller="")) == [
        (("seller",), "Value error, Name the seller when the store is Other.")
    ]
    assert model.model_validate(built(store="serverpartdeals", seller="")).seller == ""


@pytest.mark.parametrize(
    "decision",
    [
        {"decision": "ignore", "drive_id": DRIVE},
        {"decision": "ignore", "condition": "new"},
        {"decision": "match", "condition": "new"},
        {"decision": "match", "drive_id": DRIVE},
        {"decision": "keep"},
        # A decision never says what a drive is: it is made or corrected beforehand.
        {"decision": "match", "drive_id": DRIVE, "condition": "new", "mpn": "ST18000NM000J"},
        {"decision": "match", "drive_id": DRIVE, "condition": "new", "capacity_gb": 3200},
        {"decision": "match", "drive_id": DRIVE, "condition": "new", "correct_drive": True},
    ],
)
def test_a_review_decision_must_say_what_it_decides_and_nothing_else(
    decision: dict[str, str],
) -> None:
    assert refused(ReviewDecision, decision)


def test_a_match_decision_names_its_drive_by_id() -> None:
    decided = TypeAdapter(ReviewDecision).validate_python(
        {"decision": "match", "drive_id": DRIVE, "condition": "new"}
    )
    assert isinstance(decided, MatchDecision)
    assert (str(decided.drive_id), decided.condition) == (DRIVE, "new")


@pytest.mark.parametrize(
    ("edit", "field"),
    [
        ({"capacity_gb": None}, "capacity_gb"),
        ({"capacity_gb": 0}, "capacity_gb"),
        ({"specifications": None}, "specifications"),
        ({"specifications": {"media_type": None}}, "specifications"),
        ({"specifications": {"intended_use": None}}, "specifications"),
        ({"specifications": {"cache_mb": 256}}, "specifications"),
        # Its MPNs change only by declaring an alias.
        ({"mpn": "ST20000NM007D"}, "mpn"),
    ],
)
def test_a_drive_correction_cannot_clear_what_a_drive_always_has(
    edit: dict[str, object], field: str
) -> None:
    assert {loc[0] for loc, _ in refused(DriveEdit, edit)} == {field}


def test_a_blank_brand_makes_a_drive_unbranded_again() -> None:
    assert DriveEdit.model_validate({"brand": "  "}).brand is None


@pytest.mark.parametrize(
    ("rule", "field"),
    [
        ({"pattern": "(unclosed", "condition": "used"}, "pattern"),
        ({"pattern": "", "condition": "used"}, "pattern"),
        ({"pattern": r"\bmint\b", "condition": "mint"}, "condition"),
    ],
)
def test_a_condition_rule_that_cannot_work_is_refused_on_its_field(
    rule: dict[str, str], field: str
) -> None:
    assert [loc for loc, _ in refused(ConditionRule, rule)] == [(field,)]


@pytest.mark.parametrize("text", ["", "  \n "])
def test_listing_text_with_nothing_in_it_is_refused(text: str) -> None:
    assert [loc for loc, _ in refused(ListingText, {"text": text})] == [("text",)]
