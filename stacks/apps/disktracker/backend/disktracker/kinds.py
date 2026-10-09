"""The kinds of store disktracker knows: those the collector reads, each as its reader there
describes it (source_kinds.json, kept current by scripts/generate-source-kinds.sh), and stores
entered by hand, which are disktracker's own. A store's settings are checked against its
kind's description here, so nothing in the backend names a kind the collector reads."""

import json
import re
from pathlib import Path
from typing import Any

# A store whose offers are entered by hand: never collected, and with nothing to set.
MANUAL = "manual"
DESCRIBED: dict[str, dict[str, Any]] = json.loads(
    (Path(__file__).parent / "source_kinds.json").read_text()
)
KINDS: dict[str, dict[str, Any]] = {
    **{kind: {**described, "collected": True} for kind, described in DESCRIBED.items()},
    MANUAL: {
        "label": "Entered by hand",
        "collected": False,
        "page_test": False,
        "groups": [],
        "settings": [],
    },
}
# What a setting is when nothing is entered for it.
BLANK: dict[str, Any] = {"text": "", "list": [], "flag": False}


class SettingsInvalid(Exception):
    """A store's settings do not fit its kind: errors says which and why, as validation
    issues located by setting."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors


def complaint(setting: dict[str, Any], value: Any, settings: dict[str, Any]) -> str | None:
    """What is wrong with one setting's value; None when nothing is."""
    if setting["type"] == "flag":
        return None if isinstance(value, bool) else "Choose yes or no."
    if setting["type"] == "list":
        if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
            return "Enter a list."
        entered = [entry for entry in value if entry.strip()]
        return "Enter at least one." if setting["required"] and not entered else None
    if not isinstance(value, str):
        return "Enter text."
    if not value:
        if setting["required"]:
            return "Enter this."
        needed = setting["needs"] and settings.get(setting["needs"])
        return "Say which this is: the settings beside it need it." if needed else None
    if setting["pattern"] and not re.search(setting["pattern"], value):
        # Every setting with a pattern says how it should look (the collector's tests see to it).
        message: str = setting["pattern_message"]
        return message
    if setting["regex"]:
        try:
            groups = re.compile(value).groups
        except re.error as error:
            return f"Enter a regular expression ({error})."
        if setting["capturing"] and groups < 1:
            return "Put a group, ( ), around the data."
    return None


def checked_settings(kind: str, entered: dict[str, Any]) -> dict[str, Any]:
    """A store's settings as its kind takes them: each one checked, and any left out given as
    blank. SettingsInvalid says what is wrong with which."""
    described = {setting["name"]: setting for setting in KINDS[kind]["settings"]}
    errors = [
        {"type": "extra_forbidden", "loc": [name], "msg": "This kind of store has no such setting."}
        for name in entered
        if name not in described
    ]
    settings = {
        name: entered.get(name, BLANK[setting["type"]]) for name, setting in described.items()
    }
    for name, setting in described.items():
        wrong = complaint(setting, settings[name], settings)
        if wrong:
            errors.append({"type": "value_error", "loc": [name], "msg": wrong})
    if errors:
        raise SettingsInvalid(errors)
    return settings


def current_settings(kind: str, saved: dict[str, Any]) -> dict[str, Any]:
    """A source's settings as its kind has them now: blank for any added since it was saved,
    without any dropped since. Settings its kind would refuse are given as they were saved."""
    names = {setting["name"] for setting in KINDS[kind]["settings"]}
    try:
        return checked_settings(kind, {name: saved[name] for name in names if name in saved})
    except SettingsInvalid:
        return saved
