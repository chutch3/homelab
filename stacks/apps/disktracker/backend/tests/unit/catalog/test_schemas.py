from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from disktracker.catalog.schemas import (
    ConditionRule,
    DriveEdit,
    IgnoreDecision,
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


def a_price(**fields: Any) -> dict[str, Any]:
    """A price a person enters for an offer at a one-off store."""
    return {
        "mpn": "ST18000NM000J",
        "store": "other",
        "seller": "Example seller",
        "condition": "manufacturer_recertified",
        "title": "Seagate Exos X18",
        "url": "https://example.com/disk",
        "capacity_gb": 18000,
        "item_price_cents": 18900,
        "shipping_cents": 1000,
        "observed_at": "2026-09-21T12:00:00Z",
        **fields,
    }


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
    ("field", "value"),
    [
        ("mpn", ""),
        ("title", "   "),
        ("capacity_gb", 0),
        ("capacity_gb", 18000.5),
        ("capacity_gb", "18 TB"),
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
    ],
)
def test_a_price_that_does_not_fit_is_refused_on_the_field_at_fault(
    field: str, value: object
) -> None:
    assert [loc for loc, _ in refused(PriceInput, a_price(**{field: value}))] == [(field,)]


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
        (IngestionInput, a_price(item_price_cents=0, store="serverpartdeals", seller="")),
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


@pytest.mark.parametrize("field", ["mpn", "condition"])
def test_an_unidentified_price_is_refused_unless_review_is_asked_for(field: str) -> None:
    assert refused(PriceInput, a_price(**{field: None})) == [
        ((field,), "Value error, Enter this, or ask for the price to be reviewed.")
    ]
    assert PriceInput.model_validate(a_price(**{field: None}, on_unmatched="queue"))


@pytest.mark.parametrize("field", ["url", "title"])
def test_asking_for_review_needs_the_page_and_title_a_reviewer_is_shown(field: str) -> None:
    assert refused(PriceInput, a_price(**{field: None}, on_unmatched="queue")) == [
        ((field,), "Value error, A price to be reviewed needs its page and title.")
    ]


def test_a_price_names_its_offer_or_describes_it_but_not_both() -> None:
    offer_id = str(uuid4())
    named = {"offer_id": offer_id, "item_price_cents": 17900}

    assert PriceInput.model_validate(named).offer_id == UUID(offer_id)
    assert refused(PriceInput, a_price(offer_id=offer_id)) == [
        (("store",), "Value error, Leave the store out when the offer is named."),
        (("mpn",), "Value error, Leave this out when the offer is named."),
        (("condition",), "Value error, Leave this out when the offer is named."),
    ]
    assert refused(PriceInput, {"item_price_cents": 17900}) == [
        (("store",), "Value error, Choose a store."),
        (("mpn",), "Value error, Enter this, or ask for the price to be reviewed."),
        (("condition",), "Value error, Enter this, or ask for the price to be reviewed."),
    ]


@pytest.mark.parametrize("model", [PriceInput, IngestionInput])
def test_a_price_at_a_one_off_store_names_its_seller(
    model: type[PriceInput] | type[IngestionInput],
) -> None:
    assert refused(model, a_price(seller="")) == [
        (("seller",), "Value error, Name the seller when the store is Other.")
    ]
    assert model.model_validate(a_price(store="serverpartdeals", seller="")).seller == ""


@pytest.mark.parametrize(
    "decision",
    [
        {"decision": "ignore", "mpn": "ST18000NM000J"},
        {"decision": "ignore", "condition": "new"},
        {"decision": "match", "condition": "new"},
        {"decision": "match", "mpn": "ST18000NM000J"},
        {"decision": "keep"},
    ],
)
def test_a_review_decision_must_say_what_it_decides_and_nothing_else(
    decision: dict[str, str],
) -> None:
    assert refused(ReviewDecision, decision)


def test_a_match_decision_names_its_drive_by_its_canonical_mpn() -> None:
    decided: MatchDecision = TypeAdapter(ReviewDecision).validate_python(
        {"decision": "match", "mpn": " st18000nm000j", "condition": "new"}
    )
    assert isinstance(decided, MatchDecision)
    assert decided.mpn == "ST18000NM000J"


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


def test_a_match_that_corrects_its_drive_says_the_capacity_to_correct_it_to() -> None:
    match = {"decision": "match", "mpn": "P09094-H21", "condition": "refurbished"}

    assert refused(ReviewDecision, {**match, "correct_drive": True}) == [
        (("match", "capacity_gb"), "Value error, Enter the capacity to correct the drive to.")
    ]
    decided: MatchDecision | IgnoreDecision = TypeAdapter(ReviewDecision).validate_python(
        {**match, "capacity_gb": 3200, "correct_drive": True}
    )
    assert isinstance(decided, MatchDecision) and decided.correct_drive
    assert TypeAdapter(ReviewDecision).validate_python(match).correct_drive is False
