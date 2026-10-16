import re
from uuid import uuid4

from playwright.sync_api import Page, expect


def price(page: Page, **fields: object) -> dict:
    answer = page.request.post(
        "/api/prices",
        data={
            "store": "serverpartdeals",
            "seller": "",
            "mpn": "P09094-H21",
            "condition": "refurbished",
            "item_price_cents": 74500,
            "shipping_cents": 0,
            **fields,
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert answer.ok, answer.text()
    result: dict = answer.json()
    return result


def test_a_capacity_conflict_is_settled_from_review_by_correcting_the_drive(page: Page):
    # Recorded once with a capacity misread from its title; collected since as 3.2 TB.
    price(page, title="HPE P09094-H213.2TB SAS", capacity_gb=213200)
    price(
        page,
        provenance="collected",
        on_unmatched="queue",
        url="https://www.serverpartdeals.com/products/p09094-h21",
        title="HPE P09094-H21 3.2TB SAS 12GBPS Smart Carrier",
        capacity_gb=3200,
    )

    page.goto("/admin")
    # Named with its count while anything waits.
    review = page.get_by_role("region", name=re.compile("^Needs matching"))
    expect(review.get_by_role("heading", name="Needs matching (1)")).to_be_visible()
    review.get_by_role("button", name="Resolve", exact=True).click()
    form = page.get_by_role("dialog", name="Resolve offer", exact=True)
    expect(
        form.get_by_text("The store says 3.2 TB; P09094-H21 is recorded as 213.2 TB.")
    ).to_be_visible()
    form.get_by_role(
        "radio", name="The store is right: correct the drive to 3.2 TB"
    ).check()
    expect(
        form.get_by_text("This changes the capacity of every offer of P09094-H21.")
    ).to_be_visible()
    form.get_by_role("button", name="Save", exact=True).click()

    expect(form).not_to_be_visible()
    expect(review.get_by_text("Nothing to match.", exact=True)).to_be_visible()
    capacities = {
        offer["drive"]["capacity_gb"]
        for offer in page.request.get("/api/offers").json()
    }
    assert capacities == {3200}
