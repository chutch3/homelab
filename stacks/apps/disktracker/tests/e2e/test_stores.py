from playwright.sync_api import Page, expect


def test_a_store_is_switched_off_and_on_again_from_the_stores_list(page: Page) -> None:
    page.goto("/admin/stores")
    switch = page.get_by_role("switch", name="Collect from ServerPartDeals", exact=True)
    expect(switch).to_be_checked()

    # The switch's checkbox sits under its drawn track, and changes once the store is saved.
    switch.click(force=True)

    expect(page.get_by_role("row", name="ServerPartDeals")).to_contain_text("Switched off")
    page.reload()
    expect(switch).not_to_be_checked()
    switch.click(force=True)
    expect(page.get_by_role("row", name="ServerPartDeals")).not_to_contain_text("Switched off")
    page.reload()
    expect(switch).to_be_checked()
