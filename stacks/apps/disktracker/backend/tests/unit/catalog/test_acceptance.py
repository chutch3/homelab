"""What becomes of a page as collected, given what disktracker knows of it: the one judgement
ingestion acts on and a preview foresees. What is known is given; reading it is the callers'."""

from typing import Any
from uuid import UUID

import pytest

from disktracker.catalog.acceptance import Known, Seen, Verdict, judged

DRIVE, OTHER = UUID(int=1), UUID(int=2)
IDENTITY = {"mpn": "ST18000NM000J", "store": "serverpartdeals", "seller": "", "condition": "new"}
TITLE = "Seagate Exos X18 ST18000NM000J 18TB"


def seen(**fields: Any) -> Seen:
    return Seen(**{"title": TITLE, "capacity_gb": 18000, "aliases": (), "in_stock": True, **fields})


def known(**fields: Any) -> Known:
    return Known(**{"drive": DRIVE, "capacity": 18000, "owners": {}, "priced": True, **fields})


def decided(**fields: Any) -> dict[str, Any]:
    return {"ignored": False, "reviewed_title": TITLE, **fields}


def test_a_page_read_as_it_should_be_is_recorded() -> None:
    assert judged(seen(), IDENTITY, None, known()) == Verdict("recorded", capacity=18000)


def test_a_listing_a_reviewer_said_is_nothing_is_ignored() -> None:
    assert judged(seen(), None, decided(ignored=True), known()) == Verdict("ignored", "decided")


@pytest.mark.parametrize(
    ("identity", "reason"),
    [({**IDENTITY, "mpn": None}, "missing_mpn"), ({**IDENTITY, "condition": None}, "missing_condition")],
)  # fmt: skip
def test_a_page_missing_what_identifies_its_offer_waits_for_review(
    identity: dict[str, Any], reason: str
) -> None:
    assert judged(seen(), identity, None, known()) == Verdict("queued", reason)


def test_a_doubted_page_waits_for_review_and_holds_its_drives_offer_when_there_is_one() -> None:
    bundle = seen(title=f"{TITLE} 4-pack")

    assert judged(bundle, IDENTITY, None, known()) == Verdict(
        "queued", "not_a_single_drive", hold=True
    )
    assert judged(bundle, IDENTITY, None, known(drive=None, capacity=None)) == Verdict(
        "queued", "not_a_single_drive"
    )


def test_a_page_a_reviewer_decided_is_taken_as_decided_while_it_reads_as_it_did() -> None:
    """Its capacity is then its drive's, whatever the page says."""
    bundle = f"{TITLE} 4-pack"
    as_reviewed = decided(reviewed_title=bundle)

    assert judged(seen(title=bundle, capacity_gb=72000), IDENTITY, as_reviewed, known()) == (
        Verdict("recorded")
    )
    # Read otherwise, it is judged again, by its drive's capacity.
    assert judged(seen(title="HPE 960TB"), IDENTITY, as_reviewed, known()).reason == (
        "implausible_capacity"
    )


def test_a_new_drive_needs_a_capacity_and_a_known_one_keeps_its_own() -> None:
    new = known(drive=None, capacity=None, priced=False)

    assert judged(seen(capacity_gb=None), IDENTITY, None, new) == Verdict(
        "queued", "missing_capacity"
    )
    assert judged(seen(), IDENTITY, None, new) == Verdict("recorded", capacity=18000)
    assert judged(seen(capacity_gb=20000, title="Exos 20TB"), IDENTITY, None, known()) == (
        Verdict("queued", "capacity_conflict")
    )
    assert judged(seen(capacity_gb=None), IDENTITY, None, known()) == Verdict("recorded")


def test_a_page_naming_an_mpn_another_drive_goes_by_waits_whole_for_review() -> None:
    taken = known(owners={"0HNHWC": OTHER})
    new = known(drive=None, capacity=None, owners={"0HNHWC": OTHER}, priced=False)

    assert judged(seen(aliases=("0FRESH", "0HNHWC")), IDENTITY, None, taken) == Verdict(
        "queued", "alias_conflict", conflict=("0HNHWC", OTHER)
    )
    assert judged(seen(aliases=("0HNHWC",)), IDENTITY, None, new).reason == "alias_conflict"


def test_another_drives_mpn_a_reviewer_accepted_is_settled_and_only_a_new_one_reopens_review() -> (
    None
):
    """Accepted, it stays the other drive's: neither the drive's nor a conflict."""
    taken = known(owners={"0HNHWC": OTHER, "0LATER": OTHER})
    accepted = decided(settled_aliases=["0HNHWC"])

    assert judged(seen(aliases=("0HNHWC",)), IDENTITY, accepted, taken) == Verdict("recorded")
    assert judged(seen(aliases=("0HNHWC", "0LATER")), IDENTITY, accepted, taken) == Verdict(
        "queued", "alias_conflict", conflict=("0LATER", OTHER)
    )


def test_the_other_mpns_a_page_gives_are_those_no_drive_goes_by_yet_once_each() -> None:
    mine = known(owners={"0MINE": DRIVE})

    assert judged(seen(aliases=("0FRESH", "0MINE", "0FRESH")), IDENTITY, None, mine) == Verdict(
        "recorded", capacity=18000, fresh=("0FRESH",)
    )


def test_a_sold_out_page_is_recorded_at_its_last_price_and_ignored_with_none() -> None:
    sold_out = seen(in_stock=False)

    assert judged(sold_out, IDENTITY, None, known()) == Verdict("recorded", capacity=18000)
    assert judged(sold_out, IDENTITY, None, known(priced=False)) == Verdict("ignored", "sold_out")
    # A new drive is judged for its capacity before it is for a price.
    new = known(drive=None, capacity=None, priced=False)
    assert judged(seen(in_stock=False, capacity_gb=None), IDENTITY, None, new).reason == (
        "missing_capacity"
    )
