import pytest

from listing_text.listing import ListingFacts, price_in, read_listing
from listing_text.readers import condition_rules

RULES = condition_rules([(r"\bmanufacturer recertified\b", "manufacturer_recertified")])


def test_a_pasted_listing_is_read_into_the_fields_of_an_offer() -> None:
    pasted = "\n  WD Red Plus 12TB NAS Hard Drive WD120EFBX (Manufacturer Recertified) \n$219.99\nIn stock"
    assert read_listing(pasted, RULES) == ListingFacts(
        title="WD Red Plus 12TB NAS Hard Drive WD120EFBX (Manufacturer Recertified)",
        mpn="WD120EFBX",
        capacity_gb=12000,
        condition="manufacturer_recertified",
        brand="Western Digital",
        item_price_cents=21999,
    )


def test_text_that_names_nothing_keeps_only_its_first_line_as_the_title() -> None:
    assert read_listing("hello\nworld", RULES) == ListingFacts(
        "hello", None, None, None, None, None
    )


def test_the_title_is_cut_to_the_length_disktracker_keeps() -> None:
    title = read_listing("x" * 200, RULES).title
    assert title is not None and len(title) == 160


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("$219.99", 21999),
        ("Price: $1,219.99", 121999),
        ("$85", 8500),
        # Struck-out, list and saving amounts are not what the offer costs.
        ("Was $299.99\n$249.99", 24999),
        ("List Price: $500.00 Price: $450.00", 45000),
        ("MSRP $399.00 Our price $349.00", 34900),
        ("Reg. $99.99 Now $79.99", 7999),
        ("You save $50.00 $199.00", 19900),
        ("Was $299.99 only", None),
        ("no price here", None),
    ],
)
def test_the_price_is_the_first_amount_that_is_not_a_former_or_saved_one(
    text: str, expected: int | None
) -> None:
    assert price_in(text) == expected
