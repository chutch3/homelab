from uuid import uuid4

from playwright.sync_api import Page, expect


def post(page: Page, path: str, fields: dict, key: bool = True) -> dict:
    headers = {"Idempotency-Key": str(uuid4())} if key else {}
    answer = page.request.post(path, data=fields, headers=headers)
    assert answer.ok, answer.text()
    result: dict = answer.json()
    return result


def priced(page: Page, mpn: str, seller: str, **drive: object) -> str:
    made = post(
        page, "/api/drives", {"mpn": mpn, "capacity_gb": 18000, **drive}, key=False
    )
    post(page, "/api/prices", {
        "drive_id": made["id"], "store": "other", "seller": seller, "condition": "new",
        "title": f"{mpn} 18TB", "item_price_cents": 30000,
    })  # fmt: skip
    drive_id: str = made["id"]
    return drive_id


def test_a_drive_is_merged_into_another_from_its_panel(page: Page) -> None:
    target = priced(page, "ST18000NM000J", "Shop A")
    source = priced(page, "0HNHWC", "Shop B", brand="Dell")

    page.goto("/admin/drives")
    drives = page.get_by_role("table", name="Drives", exact=True)
    drives.get_by_title("ST18000NM000J 18TB", exact=True).click()
    page.get_by_role(
        "button", name="Merge another drive into this one", exact=True
    ).click()
    form = page.get_by_role(
        "dialog", name="Merge another drive into this one", exact=True
    )
    form.get_by_role("textbox", name="Drive to merge in").fill("0HNHWC")
    page.get_by_role("option", name="0HNHWC 18 TB 0HNHWC 18TB").click()
    expect(
        form.get_by_text(
            "ST18000NM000J stays, going by 0HNHWC too, with the brand Dell."
        )
    ).to_be_visible()
    form.get_by_role("button", name="Merge", exact=True).click()

    expect(form).not_to_be_visible()
    expect(page.get_by_text("Merged 0HNHWC into ST18000NM000J.")).to_be_visible()
    merged = page.request.get(f"/api/drives/{target}").json()
    offers = page.request.get("/api/offers", params={"drive_id": target}).json()
    assert (merged["aliases"], merged["brand"]) == (
        ["0HNHWC"],
        "Dell",
    )
    assert sorted(offer["seller"] for offer in offers) == ["Shop A", "Shop B"]
    assert page.request.get(f"/api/drives/{source}").status == 404
