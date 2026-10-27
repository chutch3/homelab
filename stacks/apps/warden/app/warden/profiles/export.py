from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal
from urllib.parse import quote

from warden.profiles.models import ProfileDocument
from warden.profiles.validation import validate_references


def _require_boolean(value: Any, field: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"invalid boolean in {field}")


def _require_score(value: Any, field: str) -> None:
    if type(value) is not int or not -2147483648 <= value <= 2147483647:
        raise ValueError(f"invalid score in {field}")


def export_documents(
    source: Literal["radarr", "sonarr"], profiles: Sequence[dict[str, Any]],
    formats: Sequence[dict[str, Any]], selected: Sequence[str],
) -> tuple[ProfileDocument, ...]:
    """Translate known API fields into portable values without filesystem or HTTP IO."""
    by_name = {p["name"]: p for p in profiles}
    if len(by_name) != len(profiles):
        raise ValueError("duplicate remote profile names")
    for name in selected:
        if name not in by_name:
            raise ValueError(f"unknown profile {name!r}")
    format_ids = {f["id"]: f for f in formats}
    if len(format_ids) != len(formats):
        raise ValueError("duplicate remote custom format IDs")
    used: set[int] = set()
    documents: list[ProfileDocument] = []
    for name in sorted(set(selected) if selected else by_name):
        profile = by_name[name]
        documents.append(export_quality_profile(source, profile, format_ids))
        used.update(entry["format"] for entry in profile["formatItems"])
    for format_id in sorted(used, key=lambda key: format_ids[key]["name"]):
        documents.append(export_custom_format(source, format_ids[format_id]))
    validate_references(documents)
    return tuple(documents)


def export_quality_profile(
    source: Literal["radarr", "sonarr"], profile: dict[str, Any], format_ids: dict[int, dict[str, Any]],
) -> ProfileDocument:
    name = profile["name"]
    _require_boolean(profile["upgradeAllowed"], f"profile {name!r}.upgradeAllowed")
    for field in ("minFormatScore", "cutoffFormatScore", "minUpgradeFormatScore"):
        _require_score(profile[field], f"profile {name!r}.{field}")
    allowed_fields = {
        "id", "name", "upgradeAllowed", "cutoff", "items", "minFormatScore",
        "cutoffFormatScore", "minUpgradeFormatScore", "formatItems",
    } | ({"language"} if source == "radarr" else set())
    unknown = profile.keys() - allowed_fields
    if unknown:
        raise ValueError(f"profile {name!r}: unsupported fields {sorted(unknown)}")
    qualities = []
    cutoff = None
    for item in reversed(profile["items"]):
        _require_boolean(item["allowed"], f"profile {name!r}.items.allowed")
        unknown = item.keys() - {"id", "name", "quality", "items", "allowed"}
        if unknown:
            raise ValueError(f"profile {name!r}: unsupported quality fields {sorted(unknown)}")
        children = item.get("items", [])
        quality_name = item["name"] if children else item["quality"]["name"]
        quality: dict[str, Any] = {"name": quality_name, "enabled": item["allowed"]}
        quality_id = item["id"] if children else item["quality"]["id"]
        if children:
            for child in children:
                _require_boolean(child["allowed"], f"profile {name!r}.items.items.allowed")
                if child.get("items") or child.keys() - {"id", "name", "quality", "items", "allowed"}:
                    raise ValueError(f"profile {name!r}: unsupported nested quality structure")
                if child["allowed"] != item["allowed"]:
                    raise ValueError(f"profile {name!r}: mixed enabled state inside a quality group is unsupported")
            quality["qualities"] = [child["quality"]["name"] for child in children]
        if quality_id == profile["cutoff"]:
            cutoff = quality_name
        qualities.append(quality)
    if cutoff is None:
        raise ValueError(f"profile {name!r}: unresolved cutoff")
    scores: dict[str, int] = {}
    for entry in profile["formatItems"]:
        _require_score(entry["score"], f"profile {name!r}.formatItems.score")
        format_id = entry["format"]
        if format_id not in format_ids:
            raise ValueError(f"profile {name!r}: missing custom format ID {format_id}")
        format_name = format_ids[format_id]["name"]
        if format_name in scores:
            raise ValueError(f"profile {name!r}: duplicate custom format {format_name!r}")
        scores[format_name] = entry["score"]
    portable = {
        "name": name,
        "upgrade": {"allowed": profile["upgradeAllowed"], "until_quality": cutoff, "until_score": profile["cutoffFormatScore"]},
        "min_format_score": profile["minFormatScore"],
        "min_upgrade_format_score": profile["minUpgradeFormatScore"],
        "qualities": qualities, "custom_format_scores": dict(sorted(scores.items())),
    }
    if source == "radarr":
        portable["language"] = profile["language"]["name"]
    return ProfileDocument(source, "profiles", f"{source}/profiles/{quote(name, safe='')}.yml", {
        "schema_version": 1, "quality_profiles": [portable],
    })


def export_custom_format(source: Literal["radarr", "sonarr"], raw: dict[str, Any]) -> ProfileDocument:
    _require_boolean(raw["includeCustomFormatWhenRenaming"], f"custom format {raw['name']!r}.includeCustomFormatWhenRenaming")
    if raw.keys() - {"id", "name", "includeCustomFormatWhenRenaming", "specifications"}:
        raise ValueError(f"custom format {raw['name']!r}: unsupported fields")
    specifications = []
    for specification in raw["specifications"]:
        for field in ("negate", "required"):
            _require_boolean(specification[field], f"custom format {raw['name']!r}.{field}")
        if specification.keys() - {"id", "name", "implementation", "implementationName", "infoLink", "negate", "required", "fields"}:
            raise ValueError(f"custom format {raw['name']!r}: unsupported condition fields")
        fields = specification["fields"]
        values = {field["name"]: field["value"] for field in fields}
        if len(values) != len(fields):
            raise ValueError(f"custom format {raw['name']!r}: duplicate condition field names")
        specifications.append({
            "name": specification["name"], "implementation": specification["implementation"],
            "negate": specification["negate"], "required": specification["required"], "fields": values,
        })
    return ProfileDocument(source, "custom_formats", f"{source}/custom_formats/{quote(raw['name'], safe='')}.json", {
        "name": raw["name"], "includeCustomFormatWhenRenaming": raw["includeCustomFormatWhenRenaming"],
        "specifications": specifications,
    })
