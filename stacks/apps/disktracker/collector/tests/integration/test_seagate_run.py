"""A store whose pages each carry a whole family of drives as data inside a script, read by a
sitemap source told where that data is. Seagate is one: the IronWolf Pro page lists sixteen
models, half of them with a price."""

import json
import subprocess
from typing import Any

from pytest_httpserver import HTTPServer

from tests.builders import listing_json, sitemap_settings
from tests.integration.harness import (
    ROOT,
    base_of,
    environment,
    events,
    know_listings,
    posts,
    rechecks,
    record_everything,
    run,
    serve_robots,
    source_json,
)

IRONWOLF_PRO = "/products/nas-drives/ironwolf-pro-hard-drive/"
PAGE = (ROOT / "tests/fixtures/seagate/ironwolf_pro.htm").read_text()
SETTINGS = sitemap_settings(
    product_path_pattern="^/products/",
    data_pattern=r"product_models = JSON\.parse\('(.*?)'\);",
    data_items="*.skus.*",
    data_model_field="modelNo",
    data_name_field="name",
    data_price_field="final_price",
    data_brand_field="brand",
    data_stock_field="stock_status",
    data_in_stock_value="IN_STOCK",
)


def serve_store(seagate: HTTPServer, paths: list[str]) -> None:
    serve_robots(seagate)
    base = base_of(seagate)
    entries = "".join(f"<url><loc>{base}{path}</loc></url>" for path in paths)
    seagate.expect_request("/sitemap.xml").respond_with_data(
        f"<urlset>{entries}</urlset>", content_type="text/xml"
    )
    seagate.expect_request(IRONWOLF_PRO).respond_with_data(PAGE, content_type="text/html")


def run_collector(seagate: HTTPServer, disktracker: HTTPServer) -> subprocess.CompletedProcess[str]:
    source = source_json("seagate", "sitemap", base_of(seagate), SETTINGS)
    return run(environment(disktracker, source))


def told(offers: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return [
        (
            offer["mpn"],
            offer["title"],
            offer["capacity_gb"],
            offer["item_price_cents"],
            offer["in_stock"],
        )
        for offer in offers
    ]


def test_one_page_gives_an_offer_for_each_model_it_prices(
    seagate: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_store(seagate, [IRONWOLF_PRO])
    record_everything(disktracker)
    know_listings(disktracker, [], store="seagate")

    result = run_collector(seagate, disktracker)

    assert result.returncode == 0, result.stderr
    # The eight models Seagate does not sell itself have no price, and are no offers.
    assert told([json.loads(request.data) for request in posts(disktracker)]) == [
        ("ST32000NT000", "IronWolf Pro 32TB", 32000, 139999, False),
        ("ST28000NT000", "IronWolf Pro 28TB", 28000, 122999, True),
        ("ST24000NT002", "IronWolf Pro 24TB", 24000, 105999, True),
        ("ST20000NT001", "IronWolf Pro 20TB", 20000, 87999, True),
        ("ST16000NT001", "IronWolf Pro 16TB", 16000, 57999, True),
        ("ST12000NT001", "IronWolf Pro 12TB", 12000, 45999, True),
        ("ST8000NT001", "Ironwolf Pro 8TB", 8000, 31999, True),
        ("ST4000NT001", "Ironwolf Pro 4TB", 4000, 19999, True),
    ]
    first = json.loads(posts(disktracker)[0].data)
    # The name does not say who made it; the data does.
    assert (first["source"], first["url"], first["condition"], first["brand"]) == (
        "seagate",
        f"{base_of(seagate)}{IRONWOLF_PRO}",
        "new",
        "Seagate",
    )
    assert [request.path for request, _ in seagate.log] == [
        "/robots.txt",
        "/sitemap.xml",
        IRONWOLF_PRO,
    ]
    assert events(result.stdout)[-1]["seen"] == 8


def test_a_model_its_page_no_longer_prices_is_out_of_stock_without_another_fetch(
    seagate: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_store(seagate, [IRONWOLF_PRO])
    record_everything(disktracker)
    url = f"{base_of(seagate)}{IRONWOLF_PRO}"
    # Known in stock from an earlier run; the page lists it now without a price.
    known = listing_json(
        url, store="seagate", title="IronWolf Pro 30TB", mpn="ST30000NT011", condition="new"
    )
    know_listings(disktracker, [known], store="seagate")

    result = run_collector(seagate, disktracker)

    assert result.returncode == 0, result.stderr
    assert told(rechecks(disktracker)) == [
        ("ST30000NT011", "IronWolf Pro 30TB", 18000, None, False)
    ]
    assert [request.path for request, _ in seagate.log].count(IRONWOLF_PRO) == 1


def test_an_offer_whose_page_left_the_sitemap_is_rechecked_as_its_own_model(
    seagate: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_store(seagate, [])
    record_everything(disktracker)
    url = f"{base_of(seagate)}{IRONWOLF_PRO}"
    known = [
        listing_json(url, store="seagate", title="IronWolf Pro 28TB", mpn="ST28000NT000"),
        # Recorded under an address that is no product page of the store: left alone.
        listing_json("https://elsewhere.test/a-drive", store="seagate", mpn="ST1000NT000"),
        listing_json(url, store="seagate", title="IronWolf Pro 26TB", mpn="ST26000NT000"),
    ]
    know_listings(disktracker, known, store="seagate")

    result = run_collector(seagate, disktracker)

    assert result.returncode == 0, result.stderr
    # Each is read from its own entry on the page; one the page no longer has is gone.
    assert told(rechecks(disktracker)) == [
        ("ST28000NT000", "IronWolf Pro 28TB", 18000, 122999, True),
        ("ST26000NT000", "IronWolf Pro 26TB", 18000, None, False),
    ]
    # The page they share is fetched once for them all.
    assert [request.path for request, _ in seagate.log].count(IRONWOLF_PRO) == 1
