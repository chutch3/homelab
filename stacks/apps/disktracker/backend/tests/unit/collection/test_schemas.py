"""What collection accepts: a source as it is entered, each kind's settings, a source to try,
and what a run says of itself. A source is checked as the fields of its kind, so where a
complaint is starts with the kind."""

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from disktracker.collection.schemas import (
    RunStart,
    RunUpdate,
    SourceInput,
    SourcePreviewInput,
)
from disktracker.collection.settings import KINDS, ShopifySettings

COUNTS = dict.fromkeys(("seen", "recorded", "queued", "ignored", "failed"), 0)

# Seagate: each page carries a family of models as JSON handed to a script.
EMBEDDED_DATA = {
    "data_pattern": r"product_models = JSON\.parse\('(.*?)'\);",
    "data_items": "*.skus.*",
    "data_model_field": "modelNo",
    "data_name_field": "name",
    "data_price_field": "final_price",
    "data_brand_field": "brand",
}
# A sitemap source whose pages are each one product has nothing to say about embedded data.
NO_EMBEDDED_DATA = dict.fromkeys(
    (*EMBEDDED_DATA, "data_stock_field", "data_in_stock_value"),
    "",
)


def a_source(**fields: Any) -> dict[str, Any]:
    return {
        "name": "Server Orbit",
        "kind": "shopify",
        "base_url": "https://www.serverorbit.com",
        "settings": {"collections": ["hard-drives"]},
        **fields,
    }


def accepted(model: Any, data: Any) -> dict[str, Any]:
    entered: dict[str, Any] = TypeAdapter(model).validate_python(data).model_dump()
    return entered


def refused(model: Any, data: Any) -> list[tuple[tuple[Any, ...], str]]:
    """Where each complaint about data is, and what it says."""
    with pytest.raises(ValidationError) as error:
        TypeAdapter(model).validate_python(data)
    return [(issue["loc"], issue["msg"]) for issue in error.value.errors()]


NO_ADDRESS = "Value error, Enter the store's address, starting http:// or https://."
NO_SCHEDULE = "Value error, Enter a cron schedule, e.g. 0 3 * * *."


class TestSourceInput:
    def test_a_collected_source_needs_only_a_name_type_and_url(self) -> None:
        source = accepted(SourceInput, a_source())

        assert {name: source[name] for name in ("schedule", "enabled", "basis", "transport",
                                                "obey_robots", "notes")} == {
            "schedule": "0 */8 * * *", "enabled": True, "basis": "unconfirmed",
            "transport": "direct", "obey_robots": True, "notes": "",
        }  # fmt: skip

    def test_a_store_entered_by_hand_needs_no_address_or_settings(self) -> None:
        source = accepted(SourceInput, {"name": "Server Orbit!", "kind": "manual"})

        assert (source["base_url"], source["settings"]) == ("", {})

    @pytest.mark.parametrize(
        ("fields", "field", "message"),
        [
            ({"retailer": "serverpartdeals"}, "retailer", "Extra inputs are not permitted"),
            ({"name": "!!!"}, "name", "String should match pattern '[A-Za-z0-9]'"),
            ({"base_url": ""}, "base_url", NO_ADDRESS),
            ({"base_url": "ftp://store.test"}, "base_url", NO_ADDRESS),
            ({"schedule": "nightly"}, "schedule", NO_SCHEDULE),
            ({"schedule": "0 3 * *"}, "schedule", NO_SCHEDULE),
            ({"transport": "vpn"}, "transport", "Input should be 'direct' or 'browser'"),
        ],
    )  # fmt: skip
    def test_a_source_that_cannot_be_collected_is_refused_on_the_field_at_fault(
        self, fields: dict[str, Any], field: str, message: str
    ) -> None:
        assert refused(SourceInput, a_source(**fields)) == [(("shopify", field), message)]

    def test_a_collected_source_is_refused_without_its_address_however_it_is_left_out(
        self,
    ) -> None:
        left_out = {k: v for k, v in a_source().items() if k != "base_url"}

        assert [loc for loc, _ in refused(SourceInput, left_out)] == [("shopify", "base_url")]
        assert [loc for loc, _ in refused(SourceInput, a_source(base_url=""))] == [
            ("shopify", "base_url")
        ]

    def test_a_store_entered_by_hand_may_still_be_given_an_address_but_only_a_real_one(
        self,
    ) -> None:
        manual = {"name": "Server Orbit!", "kind": "manual"}

        assert accepted(SourceInput, {**manual, "base_url": "https://orbit.test"})["base_url"]
        assert [loc for loc, _ in refused(SourceInput, {**manual, "base_url": "orbit"})] == [
            ("manual", "base_url")
        ]

    def test_a_kind_nobody_reads_is_refused_on_the_kind(self) -> None:
        with pytest.raises(ValidationError) as error:
            TypeAdapter(SourceInput).validate_python(a_source(kind="magento"))

        assert [issue["type"] for issue in error.value.errors()] == ["union_tag_invalid"]


class TestRobots:
    def test_robots_txt_is_ignored_only_with_permission_granted(self) -> None:
        for basis in ("terms_allow", "open_api", "unconfirmed"):
            assert refused(SourceInput, a_source(basis=basis, obey_robots=False)) == [
                (
                    ("shopify", "obey_robots"),
                    "Value error, robots.txt can be ignored only with permission granted.",
                )
            ]
        permitted = accepted(SourceInput, a_source(basis="permission", obey_robots=False))
        assert (permitted["basis"], permitted["obey_robots"]) == ("permission", False)

    def test_a_source_is_tried_as_it_would_be_saved(self) -> None:
        assert [loc for loc, _ in refused(SourcePreviewInput, a_source(obey_robots=False))] == [
            ("shopify", "obey_robots")
        ]


class TestSettings:
    def test_each_kind_fills_in_the_settings_left_out(self) -> None:
        shopify = accepted(SourceInput, a_source())
        sitemap = accepted(SourceInput, a_source(kind="sitemap", settings={}))
        sap = accepted(
            SourceInput,
            a_source(
                kind="sap_commerce",
                settings={"api_url": "https://api.wd.test/wdwebservices/v2", "site": "us"},
            ),
        )

        assert shopify["settings"] == {"collections": ["hard-drives"], "free_shipping": False}
        # Blank: the sitemap is found from robots.txt, every page in it is read, and each page
        # is one product read from its own markup.
        assert sitemap["settings"] == {
            "sitemap_path": "",
            "product_path_pattern": "",
            "free_shipping_marker": "",
            **NO_EMBEDDED_DATA,
        }
        assert sap["settings"] == {
            "api_url": "https://api.wd.test/wdwebservices/v2",
            "site": "us",
            "sitemap_path": "",
            "product_path_pattern": "",
            "recertified_sku_prefix": "",
        }

    def test_a_sitemap_source_can_say_where_its_pages_carry_their_products_as_data(
        self,
    ) -> None:
        source = accepted(SourceInput, a_source(kind="sitemap", settings=EMBEDDED_DATA))

        # With no stock field, a product is in stock whenever it has a price.
        assert source["settings"] == {
            "sitemap_path": "",
            "product_path_pattern": "",
            "free_shipping_marker": "",
            **EMBEDDED_DATA,
            "data_stock_field": "",
            "data_in_stock_value": "",
        }

    @pytest.mark.parametrize(
        ("kind", "settings", "field", "error"),
        [
            ("shopify", {"collections": "hard-drives"}, "collections", "list_type"),
            ("shopify", {}, "collections", "missing"),
            ("shopify", {"collections": []}, "collections", "too_short"),
            # Blank entries are no entries.
            ("shopify", {"collections": [""]}, "collections", "too_short"),
            ("shopify", {"collections": ["all"], "free_shipping": "maybe"}, "free_shipping",
             "bool_parsing"),
            ("sitemap", {"sitemap_path": 5}, "sitemap_path", "string_type"),
            ("sap_commerce", {"api_url": "https://api.wd.test", "site": ""}, "site",
             "string_too_short"),
            ("sap_commerce", {"site": "us"}, "api_url", "missing"),
        ],
    )  # fmt: skip
    def test_a_setting_of_the_wrong_shape_or_left_out_is_refused_on_the_setting(
        self, kind: str, settings: dict[str, Any], field: str, error: str
    ) -> None:
        with pytest.raises(ValidationError) as raised:
            TypeAdapter(SourceInput).validate_python(a_source(kind=kind, settings=settings))
        assert [(e["loc"], e["type"]) for e in raised.value.errors()] == [
            ((kind, "settings", field), error)
        ]

    @pytest.mark.parametrize(
        ("kind", "settings", "field", "message"),
        [
            ("sitemap", {"sitemap_path": "sitemap.xml"}, "sitemap_path", "Start it with /."),
            ("sap_commerce", {"api_url": "api.wd.test", "site": "us"}, "api_url",
             "Enter the API's address, starting http:// or https://."),
            ("sitemap", {**EMBEDDED_DATA, "data_items": "*.skus .*"}, "data_items",
             "A path has no spaces in it."),
            (
                "sitemap",
                {"product_path_pattern": "(unclosed"},
                "product_path_pattern",
                "Enter a regular expression (missing ), unterminated subpattern at position 0).",
            ),
            # Where a page's data is: a regular expression with a group around the data, and
            # then which fields name, number and price each product.
            (
                "sitemap",
                {**EMBEDDED_DATA, "data_pattern": "(unclosed"},
                "data_pattern",
                "Enter a regular expression (missing ), unterminated subpattern at position 0).",
            ),
            (
                "sitemap",
                {**EMBEDDED_DATA, "data_pattern": "models = "},
                "data_pattern",
                "Put a group, ( ), around the data.",
            ),
            *(
                (
                    "sitemap",
                    {**EMBEDDED_DATA, field: ""},
                    field,
                    "Say which this is: the settings beside it need it.",
                )
                for field in ("data_model_field", "data_name_field", "data_price_field")
            ),
        ],
    )  # fmt: skip
    def test_a_setting_that_does_not_fit_is_refused_on_the_setting_with_why(
        self, kind: str, settings: dict[str, Any], field: str, message: str
    ) -> None:
        """What each complaint says, since it is shown on the setting as it is."""
        assert refused(SourceInput, a_source(kind=kind, settings=settings)) == [
            ((kind, "settings", field), f"Value error, {message}")
        ]

    def test_a_kinds_settings_hold_to_their_rules_however_they_are_read(self) -> None:
        """The same rules whether a store is entered or its settings are read alone."""
        for settings in ({}, {"collections": []}, {"collections": [" "]}):
            with pytest.raises(ValidationError):
                ShopifySettings.model_validate(settings)
        assert ShopifySettings.model_validate({"collections": ["all"]}).collections == ["all"]

    @pytest.mark.parametrize(
        ("kind", "settings", "field"),
        [
            # Worked out by the collector, not set: the title, the store's own brands and
            # codes, which product pages name a capacity, and which pages are recertified.
            ("sitemap", {"title_prefix": "goHardDrive.com - "}, "title_prefix"),
            ("sitemap", {"own_brands": ["Avolusion"]}, "own_brands"),
            ("sitemap", {"product_code_class": "product_code"}, "product_code_class"),
            ("sitemap", {"require_capacity_in_url": True}, "require_capacity_in_url"),
            (
                "sap_commerce",
                {"api_url": "https://api.wd.test", "site": "us", "recertified_path": "/r/"},
                "recertified_path",
            ),
            ("shopify", {"collections": ["all"], "site": "us"}, "site"),
            # Worked out by the collector, not set: a SKU in a title is the MPN.
            ("shopify", {"collections": ["all"], "mpn_from_sku": True}, "mpn_from_sku"),
            # Sold-out prices are never recorded, so there is no placeholder to tell apart.
            ("shopify", {"collections": ["all"], "placeholder_price": "100.00"}, "placeholder_price"),
            ("manual", {"collections": ["all"]}, "collections"),
        ],
    )  # fmt: skip
    def test_a_setting_the_kind_does_not_have_is_refused(
        self, kind: str, settings: dict[str, Any], field: str
    ) -> None:
        source = a_source(kind=kind, settings=settings)
        with pytest.raises(ValidationError) as raised:
            TypeAdapter(SourceInput).validate_python(source)
        assert [(e["loc"], e["type"]) for e in raised.value.errors()] == [
            ((kind, "settings", field), "extra_forbidden")
        ]

    def test_a_kinds_saved_settings_are_given_without_any_it_has_since_dropped(self) -> None:
        """Read back, a store saved before a setting was dropped reads as if saved today; one
        added since is left to its blank, and nothing is checked again."""
        saved = {"product_path_pattern": "-p/", "title_prefix": "Old Store - "}

        assert KINDS["sitemap"].settings.saved(saved) == {"product_path_pattern": "-p/"}
        assert KINDS["shopify"].settings.saved({}) == {}


class TestKinds:
    def test_a_store_entered_by_hand_is_never_collected_and_has_nothing_to_set(self) -> None:
        assert KINDS["manual"].described() == {
            "label": "Entered by hand",
            "collected": False,
            "page_test": False,
            "groups": [],
            "settings": [],
        }

    def test_each_kind_is_described_by_its_settings_model(self) -> None:
        """The Admin form is drawn from this: what a kind of store needs to know is written
        once, as its settings model."""
        shopify, sitemap = KINDS["shopify"].described(), KINDS["sitemap"].described()

        assert (shopify["label"], shopify["collected"], shopify["page_test"]) == (
            "Shopify",
            True,
            False,
        )
        assert [(s["name"], s["type"], s["required"]) for s in shopify["settings"]] == [
            ("collections", "list", True),
            ("free_shipping", "flag", False),
        ]
        assert sitemap["page_test"] is True
        assert sitemap["groups"] == [
            {
                "name": "data",
                "label": "Pages that list several products",
                "help": "For a store whose page covers a whole family of drives and carries them"
                " as JSON inside a script. Left blank, each page is one product, read from its"
                " own price markup.",
            }
        ]
        # Every setting a sitemap store is saved with is one its kind describes.
        assert [s["name"] for s in sitemap["settings"]] == [
            *("sitemap_path", "product_path_pattern", "free_shipping_marker"),
            *NO_EMBEDDED_DATA,
        ]


PAGE = "https://www.seagate.com/products/nas-drives/ironwolf-pro-hard-drive/"


class TestPagePreview:
    def test_a_sitemap_source_can_be_tried_on_one_of_its_pages(self) -> None:
        preview = accepted(
            SourcePreviewInput,
            {"name": "Seagate", "kind": "sitemap", "base_url": "https://www.seagate.com",
             "page_url": PAGE},
        )  # fmt: skip

        assert preview["page_url"] == PAGE

    @pytest.mark.parametrize(
        ("source", "complaint"),
        [
            (
                a_source(page_url=PAGE),
                (("shopify", "page_url"),
                 "Value error, This kind of store cannot be tested on one page."),
            ),
            (
                {"name": "Seagate", "kind": "sitemap", "base_url": "https://www.seagate.com",
                 "page_url": "ironwolf-pro"},
                (("sitemap", "page_url"),
                 "Value error, Enter the page's address, starting http:// or https://."),
            ),
        ],
        ids=["a kind that reads no pages", "not an address"],
    )  # fmt: skip
    def test_a_page_that_cannot_be_tried_is_refused_on_the_page(
        self, source: dict[str, Any], complaint: tuple[tuple[str, ...], str]
    ) -> None:
        assert refused(SourcePreviewInput, source) == [complaint]


STARTED = "2026-09-27T16:00:00Z"


class TestRunReports:
    @pytest.mark.parametrize(
        ("body", "field"),
        [
            ({**COUNTS, "seen": -1}, ("seen",)),
            ({**COUNTS, "seen": "4"}, ("seen",)),
            ({"seen": 1}, ("recorded",)),
            ({**COUNTS, "status": "completed"}, ()),
            ({**COUNTS, "status": "running", "finished_at": STARTED}, ()),
            ({**COUNTS, "status": "completed", "finished_at": "2026-09-27T16:10:00"},
             ("finished_at",)),
            ({**COUNTS, "status": "abandoned", "finished_at": STARTED}, ("status",)),
        ],
        ids=["negative", "not a number", "counts left out", "ended without when",
             "running with an end", "an end without a zone", "abandoned is not said by a run"],
    )  # fmt: skip
    def test_what_a_run_says_must_make_sense(
        self, body: dict[str, Any], field: tuple[str, ...]
    ) -> None:
        assert refused(RunUpdate, body)[0][0] == field

    def test_a_run_that_ends_says_when_and_one_still_running_does_not(self) -> None:
        assert refused(RunUpdate, {**COUNTS, "status": "failed"}) == [
            ((), "Value error, A run that has ended says when; one still running does not.")
        ]
        assert accepted(RunUpdate, COUNTS)["status"] == "running"
        assert accepted(RunUpdate, {**COUNTS, "status": "stopped", "finished_at": STARTED})[
            "finished_at"
        ]

    def test_a_run_starts_at_a_moment_in_a_known_zone(self) -> None:
        start = {"id": "0f0e2d8c-5b1a-4c2e-9d7a-2b1c0e9f8a7b", "source": "goharddrive"}

        assert [
            loc for loc, _ in refused(RunStart, {**start, "started_at": "2026-09-27T08:00:00"})
        ] == [("started_at",)]
        assert [
            loc for loc, _ in refused(RunStart, {**start, "source": "", "started_at": STARTED})
        ] == [("source",)]


class TestRunCause:
    def test_a_failed_run_may_say_why_and_no_other_does(self) -> None:
        ended = {**COUNTS, "finished_at": STARTED}

        failed = accepted(RunUpdate, {**ended, "status": "failed", "reason": "HTTP 503"})
        assert failed["reason"] == "HTTP 503"
        assert accepted(RunUpdate, {**ended, "status": "failed"})["reason"] is None
        for status in ("completed", "stopped"):
            assert refused(RunUpdate, {**ended, "status": status, "reason": "x"}) == [
                (("reason",), "Value error, Only a failed run says why.")
            ]
        assert [loc for loc, _ in refused(RunUpdate, {**COUNTS, "reason": "x"})] == [("reason",)]
