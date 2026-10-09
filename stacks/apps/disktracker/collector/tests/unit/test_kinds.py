"""Each reader describes the settings its kind of source has. disktracker's backend checks a
store's settings against that description and its Admin form is drawn from it, so the
description is the only place a kind's settings are written down."""

from typing import Any

import pytest

from collector.container import Container
from collector.kinds import described
from collector.ports import Description, Reader

READERS: dict[str, Reader[Any]] = Container().readers()
BLANK = {"text": "", "list": ["one"], "flag": False}


def blank(description: Description) -> dict[str, Any]:
    """Settings as disktracker gives them when nothing is set: every one, at its default."""
    return {setting.name: BLANK[setting.type] for setting in description.settings}


@pytest.mark.parametrize("kind", sorted(READERS))
def test_a_reader_reads_exactly_the_settings_it_describes(kind: str) -> None:
    reader = READERS[kind]
    settings = blank(reader.description)
    if kind == "sap_commerce":
        settings |= {"api_url": "https://api.example.com/occ/v2", "site": "us"}
    # Everything it reads is described: it reads the described settings without complaint.
    reader.settings(settings)
    # And everything described is read: each one left out is missed.
    for name in settings:
        with pytest.raises(KeyError, match=name):
            reader.settings({key: value for key, value in settings.items() if key != name})


def test_every_kind_is_described_as_data_for_disktracker() -> None:
    kinds = described()
    assert sorted(kinds) == ["sap_commerce", "shopify", "sitemap"]
    assert kinds["shopify"] == {
        "label": "Shopify",
        "page_test": False,
        "groups": [],
        "settings": [
            {
                "name": "collections",
                "label": "Collections",
                "type": "list",
                "required": True,
                "description": "Comma-separated collection handles",
                "placeholder": "hard-drives, solid-state-drives",
                "group": "",
                "pattern": "",
                "pattern_message": "",
                "regex": False,
                "capturing": False,
                "needs": "",
            },
            {
                "name": "free_shipping",
                "label": "Every order ships free",
                "type": "flag",
                "required": False,
                "description": "",
                "placeholder": "",
                "group": "",
                "pattern": "",
                "pattern_message": "",
                "regex": False,
                "capturing": False,
                "needs": "",
            },
        ],
    }
    sitemap = kinds["sitemap"]
    assert (sitemap["label"], sitemap["page_test"]) == ("Sitemap + product page", True)
    assert [group["name"] for group in sitemap["groups"]] == ["data"]
    by_name = {setting["name"]: setting for setting in sitemap["settings"]}
    assert (by_name["data_pattern"]["regex"], by_name["data_pattern"]["capturing"]) == (True, True)
    assert by_name["data_model_field"]["needs"] == "data_pattern"
    assert by_name["sitemap_path"]["pattern"] == r"^(/\S*)?$"


@pytest.mark.parametrize("kind", sorted(READERS))
def test_a_setting_that_must_look_a_certain_way_says_how_when_it_does_not(kind: str) -> None:
    # disktracker shows this message as it is: there is no other to fall back on.
    wordless = [
        setting.name
        for setting in READERS[kind].description.settings
        if setting.pattern and not setting.pattern_message
    ]
    assert wordless == []
