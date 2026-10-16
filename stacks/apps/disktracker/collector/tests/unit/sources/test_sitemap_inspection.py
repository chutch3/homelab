import json

import pytest

from collector.sources.sitemap import embedded_settings, json_ld_says, path_pattern


def parsed(data: object) -> str:
    """A script that hands a page its data as a string to parse, as Seagate's does."""
    return f"<script>page.models = JSON.parse('{json.dumps(data)}');</script>"


def test_products_in_a_pages_data_are_found_with_the_fields_that_describe_them() -> None:
    page = parsed(
        {
            "props": {
                "related": [{"title": "A cable", "price": "5.00"}],
                "products": [
                    {
                        "title": "Exos 4TB",
                        "sku": "ST4000NM000A",
                        "listPrice": "99.00",
                        "salePrice": "89.00",
                        "vendor": "Seagate",
                        "stock": "In Stock",
                        "stock_code": "IN_STOCK",
                    },
                    {"title": "Exos 8TB", "sku": "ST8000NM000A", "listPrice": "150.00"},
                ],
            }
        }
    )
    assert embedded_settings(page) == {
        "data_pattern": r"models = JSON\.parse\('(.*?)'\);",
        "data_items": "props.products.*",
        "data_model_field": "sku",
        "data_name_field": "title",
        # The field that names a sale comes before a list price.
        "data_price_field": "salePrice",
        "data_brand_field": "vendor",
        # The one written as a code comes before the one written for people.
        "data_stock_field": "stock_code",
        "data_in_stock_value": "IN_STOCK",
    }


def test_data_that_is_one_product_needs_no_path_to_its_products() -> None:
    found = embedded_settings(parsed({"name": "Exos 4TB", "mpn": "ST4000NM000A", "price": 89}))
    assert found is not None
    assert (found["data_items"], found["data_price_field"], found["data_stock_field"]) == (
        # Blank: the data is the product. And it does not say whether it is in stock.
        "",
        "price",
        "",
    )


OWN_SCRIPT = (
    '<script id="data" type="application/json">'
    '[{"name": "Exos 4TB", "mpn": "ST4000NM000A", "price": 89}]</script>'
)


@pytest.mark.parametrize(
    "page",
    [
        "<p>no scripts</p>",
        # Data in a script of its own is not looked for: no store read yet carries it so.
        OWN_SCRIPT,
        parsed({"products": [{"title": "A cable", "price": "5.00", "sku": "CAB-0001"}]}),
        parsed({"products": [{"title": "Exos 4TB", "sku": "ST4000NM000A"}]}),
        parsed({"products": [{"title": "Exos 4TB", "price": "89.00"}]}),
        "<script>x = JSON.parse('[1, 2]'); y = JSON.parse('{bad');</script>",
    ],
    ids=[
        "no data",
        "data not handed to JSON.parse",
        "no capacity",
        "no price",
        "no model",
        "nothing like a product",
    ],
)
def test_a_page_whose_scripts_carry_no_products_gives_no_settings(page: str) -> None:
    assert embedded_settings(page) is None


def test_whether_a_product_is_in_stock_is_read_only_from_what_is_written_as_text() -> None:
    found = embedded_settings(
        parsed([{"name": "Exos 4TB", "mpn": "ST4000NM000A", "price": 89, "inStock": True}])
    )
    assert found is not None
    assert (found["data_stock_field"], found["data_in_stock_value"]) == ("", "")


def test_the_data_with_the_most_priced_products_is_chosen() -> None:
    few = [{"name": "Exos 4TB", "mpn": "ST4000NM000A", "price": 89}]
    many = [*few, {"name": "Exos 8TB", "mpn": "ST8000NM000A", "price": 150}]
    page = (
        f"<script>a.featured = JSON.parse('{json.dumps(few)}');"
        f" a.all_models = JSON.parse('{json.dumps(many)}');</script>"
    )
    found = embedded_settings(page)
    assert found is not None
    assert found["data_pattern"] == r"all_models = JSON\.parse\('(.*?)'\);"


@pytest.mark.parametrize(
    ("path", "listed", "pattern"),
    [
        ("/products/nas/ironwolf/", ["/products/nas/ironwolf/", "/products/exos/"], "^/products/"),
        ("/A-4TB-p/g1.htm", ["/A-4TB-p/g1.htm", "/B-8TB-p/g2.htm", "/Drives-s/1.htm"], "-p/"),
        ("/a-4tb-drive/", ["/a-4tb-drive/", "/b-8tb-drive/"], ""),
        ("/A-4TB-Drive", ["/A-4TB-Drive", "/B-8TB", "/drives/sata/8tb"], "^/[^/]+/?$"),
        ("/shop/a-4tb-drive/", ["/shop/a-4tb-drive/", "/about/us/"], ""),
        ("/A-4TB-p/g1.htm", ["/A-4TB-p/g1.htm", "/Drives-s/1.htm"], ""),
        ("/products/x/", [], ""),
    ],
    ids=[
        "a shared first part",
        "a shared ending",
        "one part",
        "one part, others deeper",
        "alone",
        "ending alone",
        "no list",
    ],
)
def test_what_product_pages_share_in_their_paths(
    path: str, listed: list[str], pattern: str
) -> None:
    assert path_pattern(path, listed) == pattern


def test_data_no_pattern_can_single_out_is_passed_over() -> None:
    drive = [{"name": "Exos 4TB", "mpn": "ST4000NM000A", "price": 89}]
    # Two pieces of data under one name: a pattern for the name finds only the first.
    page = (
        f"<script>a.models = JSON.parse('[]'); b.models = JSON.parse('{json.dumps(drive)}');"
        "</script>"
    )
    assert embedded_settings(page) is None


UNREADABLE = '<script type="application/ld+json">{not json</script>'


@pytest.mark.parametrize(
    ("scripts", "said"),
    [
        ("", "and it has no JSON-LD"),
        (
            '<script type="application/ld+json">{"@type": "Product", "name": "A drive"}</script>',
            "and its JSON-LD describes a product without a price",
        ),
        (
            UNREADABLE
            + '<script type="application/ld+json">{"@type": "https://schema.org/WebPage"}</script>',
            "and its JSON-LD describes no product (it describes: WebPage)",
        ),
        (
            '<script type="application/ld+json">{"name": "untyped"}</script>',
            "and its JSON-LD describes no product (it describes: nothing)",
        ),
    ],
    ids=["none", "a product unpriced", "other things", "nothing typed"],
)
def test_what_a_pages_json_ld_has_to_do_with_there_being_no_price(scripts: str, said: str) -> None:
    assert json_ld_says(f"<title>A 4TB drive</title>{scripts}") == said
