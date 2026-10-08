"""A kind of source's settings are written once, as a dataclass's fields: its description and
how a store's saved settings are read both come from them."""

from dataclasses import dataclass
from typing import Any

import pytest

from collector.ports import Description, Group, Setting
from collector.settings import described, setting, settings_from


@dataclass(frozen=True)
class ExampleSettings:
    feeds: tuple[str, ...] = setting("Feeds", type="list", required=True)
    path: str = setting("Path", placeholder="/feed.xml", group="more")
    free: bool = setting("Ships free", type="flag")


SAVED: dict[str, Any] = {"feeds": ["a", "b"], "path": "/feed.xml", "free": True}


def test_a_kind_is_described_by_the_fields_of_its_settings() -> None:
    groups = (Group("more", "More", "Seldom needed."),)
    assert described("Example", ExampleSettings, groups) == Description(
        "Example",
        (
            Setting("feeds", "Feeds", type="list", required=True),
            Setting("path", "Path", placeholder="/feed.xml", group="more"),
            Setting("free", "Ships free", type="flag"),
        ),
        groups,
    )


def test_saved_settings_are_read_as_the_class_with_a_list_kept_in_order() -> None:
    assert settings_from(ExampleSettings, SAVED) == ExampleSettings(
        feeds=("a", "b"), path="/feed.xml", free=True
    )


def test_what_is_saved_beyond_the_settings_described_is_left_alone() -> None:
    read = settings_from(ExampleSettings, {**SAVED, "dropped_long_ago": "x"})
    assert read == ExampleSettings(feeds=("a", "b"), path="/feed.xml", free=True)


@pytest.mark.parametrize("name", ["feeds", "path", "free"])
def test_a_setting_left_out_is_missed_by_name(name: str) -> None:
    with pytest.raises(KeyError, match=name):
        settings_from(ExampleSettings, {key: value for key, value in SAVED.items() if key != name})


@pytest.mark.parametrize(
    ("name", "saved", "complaint"),
    [
        ("path", None, "path is not text"),
        ("path", 5, "path is not text"),
        ("free", "false", "free is neither on nor off"),
        ("free", 1, "free is neither on nor off"),
        ("feeds", "a, b", "feeds is not a list of texts"),
        ("feeds", ["a", 2], "feeds is not a list of texts"),
    ],
)
def test_a_setting_saved_as_the_wrong_sort_of_thing_is_refused_not_guessed_at(
    name: str, saved: object, complaint: str
) -> None:
    # Read as it stands, "false" would be a flag that is on, and nothing a path called "None".
    with pytest.raises(TypeError, match=complaint):
        settings_from(ExampleSettings, {**SAVED, name: saved})
