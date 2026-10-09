"""A kind of source's settings, written down once: as the fields of a dataclass, each saying
how disktracker asks for it and checks it. The reader's description (what the Admin form is
drawn from) and how a store's saved settings are read both come from those fields, so they
cannot disagree."""

from collections.abc import Mapping
from dataclasses import field, fields
from typing import Any

from collector.ports import Description, Group, Setting


def as_saved(name: str, kind: str, value: object) -> Any:
    """A saved setting's value, as the reader takes it: a text, a flag, or the texts of a
    list in a tuple. A value of another sort is refused by name: read as it stands, "false"
    would be a flag that is on."""
    if kind == "flag" and isinstance(value, bool):
        return value
    if kind == "text" and isinstance(value, str):
        return value
    if kind == "list" and isinstance(value, list) and all(isinstance(e, str) for e in value):
        return tuple(value)
    sorts = {"text": "not text", "flag": "neither on nor off", "list": "not a list of texts"}
    raise TypeError(f"{name} is {sorts[kind]}")


def setting(label: str, *, type: str = "text", **said: Any) -> Any:
    """A dataclass field that is a setting: label is what the form calls it, and the rest is
    as Setting has it (required, description, placeholder, group, pattern, ...)."""
    return field(metadata={"setting": {"label": label, "type": type, **said}})


def described(label: str, settings: type, groups: tuple[Group, ...] = ()) -> Description:
    """A kind of source called label, with the settings this class has."""
    return Description(
        label,
        tuple(
            Setting(name=entry.name, **entry.metadata["setting"])
            for entry in fields(settings)
            if "setting" in entry.metadata
        ),
        groups,
    )


def settings_from[S](settings: type[S], saved: Mapping[str, Any]) -> S:
    """A store's settings as disktracker saved them, read as this class: every one is given
    (disktracker fills in what was left blank), so one missing is a KeyError naming it."""
    return settings(
        **{
            entry.name: as_saved(entry.name, entry.metadata["setting"]["type"], saved[entry.name])
            for entry in fields(settings)  # type: ignore[arg-type]
            if "setting" in entry.metadata
        }
    )
