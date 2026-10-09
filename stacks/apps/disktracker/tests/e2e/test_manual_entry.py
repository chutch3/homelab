from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Page, Route, expect


def add_price(page: Page, title: str, mpn: str, capacity: str, item: str, shipping: str = "") -> None:
    page.get_by_role("button", name="Add offer", exact=True).click()
    form = page.get_by_role("dialog", name="Add offer", exact=True)
    form.get_by_text("More details", exact=True).click()
    form.get_by_label("Offer title", exact=True).fill(title)
    form.get_by_label("MPN", exact=True).fill(mpn)
    form.get_by_label("Capacity", exact=True).select_option(capacity)
    form.get_by_label("Store", exact=True).select_option("other")
    form.get_by_label("Seller name", exact=True).fill("Example seller")
    form.get_by_label("Condition", exact=True).select_option("manufacturer_recertified")
    form.get_by_label("Item price (USD)", exact=True).fill(item)
    form.get_by_label("Shipping & fees (USD)", exact=True).fill(shipping)
    form.get_by_role("button", name="Save offer", exact=True).click()
    expect(form).not_to_be_visible()


@pytest.mark.parametrize("application_url", ["/", "/absproxy/5173/"], indirect=True)
def test_record_prices_then_fix_edit_and_delete_the_offer(page: Page, application_url: str) -> None:
    page.set_default_timeout(5000)
    requests: list[str] = []
    page.on("request", lambda request: requests.append(request.url))
    page.goto(application_url)
    expect(page.get_by_role("button", name="Add offer", exact=True)).to_be_visible()
    base_path = urlsplit(application_url).path
    assert all(urlsplit(url).path.startswith(base_path) for url in requests), requests
    page.get_by_role("button", name="Add offer", exact=True).click()
    form = page.get_by_role("dialog", name="Add offer", exact=True)
    form.get_by_text("More details", exact=True).click()
    form.get_by_label("Offer title", exact=True).fill("Seagate Exos X18")
    form.get_by_label("MPN", exact=True).fill("ST18000NM000J")
    form.get_by_label("Capacity", exact=True).select_option("18000")
    form.get_by_label("Store", exact=True).select_option("other")
    form.get_by_label("Seller name", exact=True).fill("Example seller")
    form.get_by_label("Store page URL", exact=True).fill("https://example.com/disk")
    form.get_by_label("Condition", exact=True).select_option("manufacturer_recertified")
    form.get_by_label("Item price (USD)", exact=True).fill("189.00")
    form.get_by_label("Shipping & fees (USD)", exact=True).fill("10.00")
    form.get_by_role("button", name="Save offer", exact=True).click()
    expect(form).not_to_be_visible()
    row = page.get_by_role("row").filter(
        has=page.get_by_role("button", name="Seagate Exos X18", exact=True)
    )
    expect(row).to_contain_text("$199.00")
    expect(row).to_contain_text("$11.06")
    page.get_by_label("Search drives", exact=True).fill("ST18000NM000J")
    expect(row).to_be_visible()

    # Corrections live on the Admin page.
    page.get_by_role("link", name="Admin", exact=True).click()
    expect(page.get_by_role("heading", name="Admin", exact=True)).to_be_visible()
    page.get_by_role("link", name="Drives", exact=True).click()
    drives = page.get_by_role("table", name="Drives", exact=True)
    page.get_by_label("Search drives", exact=True).fill("ST18000NM000J")
    drives.get_by_role("button", name="Seagate Exos X18", exact=True).click()
    page.get_by_role("button", name="Edit specifications", exact=True).click()
    specs_form = page.get_by_role("dialog", name="Edit specifications", exact=True)
    specs_form.get_by_label("Recording type", exact=True).select_option("cmr")
    specs_form.get_by_role("button", name="Save", exact=True).click()
    expect(specs_form).not_to_be_visible()
    page.get_by_role("button", name="Specifications", exact=True).click()
    specs = page.get_by_role("region", name="Drive specifications", exact=True)
    expect(specs.get_by_text("CMR", exact=True)).to_be_visible()
    page.keyboard.press("Escape")
    page.get_by_role("link", name="Prices", exact=True).click()

    page.get_by_text("More filters", exact=True).click()
    page.get_by_label("Recording type", exact=True).select_option("cmr")
    expect(row).to_be_visible()
    row.get_by_role("button", name="Seagate Exos X18", exact=True).click()
    offers = page.get_by_role("table", name="Offers", exact=True)
    # A later price is typed under the offer itself; shipping stays as last recorded.
    offers.get_by_role("button", name="Record price", exact=True).click()
    price = offers.get_by_label("New price for Seagate Exos X18", exact=True)
    price.fill("179.00")
    price.press("Enter")
    expect(page.get_by_role("status")).to_contain_text("Recorded $179.00 for Seagate Exos X18.")

    page.reload()
    expect(page.get_by_label("Search drives", exact=True)).to_have_value("ST18000NM000J")
    page.get_by_role("button", name="Seagate Exos X18", exact=True).click()
    page.get_by_role("button", name="Price history (2)", exact=True).click()
    history = page.get_by_role("table", name="Price history", exact=True)
    expect(history.get_by_role("row")).to_have_count(3)
    expect(history).to_contain_text("$199.00")
    expect(history).to_contain_text("$189.00")
    page.keyboard.press("Escape")

    page.get_by_role("link", name="Admin", exact=True).click()
    page.get_by_role("link", name="Drives", exact=True).click()
    drives.get_by_role("button", name="Seagate Exos X18", exact=True).click()
    page.get_by_role("button", name="Price history (2)", exact=True).click()

    # The $179 price was a typo: delete it rather than correcting it.
    history.get_by_role("button", name="Delete price", exact=True).last.click()
    confirm = page.get_by_role("dialog", name="Delete price", exact=True)
    expect(confirm).to_contain_text("$179.00")
    confirm.get_by_role("button", name="Delete", exact=True).click()
    expect(confirm).not_to_be_visible()
    expect(history.get_by_role("row")).to_have_count(2)
    expect(offers).to_contain_text("$199.00")

    page.get_by_role("button", name="More actions for Example seller", exact=True).click()
    page.get_by_role("menuitem", name="Edit offer", exact=True).click()
    edit = page.get_by_role("dialog", name="Edit offer", exact=True)
    edit.get_by_label("Offer title", exact=True).fill("Seagate Exos X18 18TB")
    edit.get_by_role("button", name="Save", exact=True).click()
    expect(edit).not_to_be_visible()
    expect(page.get_by_role("dialog", name="Seagate Exos X18 18TB", exact=True)).to_be_visible()

    page.get_by_role("button", name="More actions for Example seller", exact=True).click()
    page.get_by_role("menuitem", name="Delete offer", exact=True).click()
    delete = page.get_by_role("dialog", name="Delete offer", exact=True)
    delete.get_by_role("button", name="Delete", exact=True).click()
    expect(delete).not_to_be_visible()
    page.reload()
    assert page.request.get(f"{application_url}api/listings").json() == []
    assert all(urlsplit(url).path.startswith(base_path) for url in requests), requests


def test_retry_after_lost_save_response_does_not_duplicate_the_price(page: Page) -> None:
    page.goto("/")
    page.get_by_role("button", name="Add offer", exact=True).click()
    form = page.get_by_role("dialog", name="Add offer", exact=True)
    form.get_by_text("More details", exact=True).click()
    form.get_by_label("Offer title", exact=True).fill("Retry test drive")
    form.get_by_label("MPN", exact=True).fill("WUH721212ALE6L4")
    form.get_by_label("Capacity", exact=True).select_option("12000")
    form.get_by_label("Store", exact=True).select_option("other")
    form.get_by_label("Seller name", exact=True).fill("Example seller")
    form.get_by_label("Condition", exact=True).select_option("used")
    form.get_by_label("Item price (USD)", exact=True).fill("150.00")
    form.get_by_label("Shipping & fees (USD)", exact=True).fill("0")

    def lose_acknowledgement(route: Route) -> None:
        response = route.fetch()
        assert response.status == 201
        # Chromium silently retries a POST after a connection reset; a plain failure is not retried.
        route.abort("failed")

    page.route("**/api/prices", lose_acknowledgement, times=1)
    form.get_by_role("button", name="Save offer", exact=True).click()
    expect(form.get_by_role("alert")).to_be_visible()
    form.get_by_role("button", name="Save offer", exact=True).click()
    expect(form).not_to_be_visible()
    page.reload()
    expect(page.get_by_role("table", name="Drive prices").get_by_role("row")).to_have_count(2)
    [offer] = page.request.get("/api/listings").json()
    [history] = page.request.get("/api/price-history", params={"listing": offer["id"]}).json()
    assert len(history["observations"]) == 1


def test_blank_shipping_and_fees_count_as_free_so_every_total_is_known(page: Page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("/")
    add_price(page, "Free shipping drive", "ST12000VN0008", "12000", "140")
    row = page.get_by_role("row").filter(
        has=page.get_by_role("button", name="Free shipping drive", exact=True)
    )
    expect(row).to_contain_text("$140.00")
    expect(row).to_contain_text("$11.67")
    expect(row).not_to_contain_text("Unknown")
    row.get_by_role("button", name="Free shipping drive", exact=True).click()
    page.get_by_role("table", name="Offers", exact=True).get_by_role(
        "button", name="Record price", exact=True
    ).click()
    # A price with its own shipping goes through the full form.
    page.get_by_role("button", name="More options", exact=True).click()
    entry = page.get_by_role("dialog", name="Record price", exact=True)
    entry.get_by_label("Item price (USD)", exact=True).fill("130")
    entry.get_by_label("Shipping & fees (USD)", exact=True).fill("12.50")
    entry.get_by_role("button", name="Save price", exact=True).click()
    expect(entry).not_to_be_visible()
    page.reload()
    expect(row).to_contain_text("$142.50")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
