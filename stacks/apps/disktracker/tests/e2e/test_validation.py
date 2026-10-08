from playwright.sync_api import Page, expect


def test_a_price_without_an_item_price_is_refused_without_losing_other_inputs(page: Page):
    page.goto("/")
    page.get_by_role("button", name="Add offer", exact=True).click()
    form = page.get_by_role("dialog", name="Add offer", exact=True)
    form.get_by_text("More details", exact=True).click()
    form.get_by_label("Offer title", exact=True).fill("Validated drive")
    form.get_by_label("MPN", exact=True).fill("ST18000NM000J")
    form.get_by_label("Store", exact=True).select_option("other")
    form.get_by_label("Seller name", exact=True).fill("Example seller")
    form.get_by_label("Condition", exact=True).select_option("refurbished")
    form.get_by_label("Capacity", exact=True).select_option("18000")
    form.get_by_label("Notes", exact=True).fill("Keep these notes")
    form.get_by_role("button", name="Save offer", exact=True).click()

    item = form.get_by_label("Item price (USD)", exact=True)
    expect(item).to_have_attribute("aria-invalid", "true")
    expect(item).to_have_accessible_description("Enter the item price.")
    expect(item).to_be_focused()
    expect(form.get_by_label("Seller name", exact=True)).to_have_value("Example seller")
    expect(form.get_by_label("Notes", exact=True)).to_have_value("Keep these notes")
    assert page.request.get("/api/listings").json() == []

    item.fill("189.00")
    form.get_by_role("button", name="Save offer", exact=True).click()
    expect(form).not_to_be_visible()
    page.reload()
    expect(page.get_by_role("button", name="Validated drive", exact=True)).to_be_visible()
    saved = page.request.get("/api/listings").json()
    assert len(saved) == 1
    assert saved[0]["condition"] == "refurbished"
    assert saved[0]["latest"]["total_cents"] == 18900
    assert saved[0]["latest"]["notes"] == "Keep these notes"
