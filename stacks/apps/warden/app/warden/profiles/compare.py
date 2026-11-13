from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from warden.profiles.models import ProfileDocument
from warden.profiles.validation import validate_references
from warden.profiles.export import export_custom_format, export_quality_profile


def select_profiles(
    source: Literal["radarr", "sonarr"], documents: Sequence[ProfileDocument], selected: Sequence[str] | None,
) -> list[str]:
    available = {
        p["name"] for d in documents if d.source == source and d.kind == "profiles"
        for p in d.data["quality_profiles"]
    }
    if selected is None:
        if not available:
            raise ValueError(f"{source}: no compatible profiles in the configuration")
        return sorted(available)
    for name in selected:
        if name not in available:
            raise ValueError(f"{source}: unknown profile {name!r}")
    return sorted(set(selected))


def _profile(data: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
    result = {key: value for key, value in data.items() if key != "description"}
    result["qualities"] = [{"enabled": True, **quality} for quality in data["qualities"]]
    if "language" not in desired:
        result.pop("language", None)
    return result


def _format(data: dict[str, Any]) -> dict[str, Any]:
    specifications = {}
    for specification in data["specifications"]:
        name = specification["name"]
        if name in specifications:
            raise ValueError(f"custom format {data['name']!r}: duplicate condition {name!r}")
        fields = specification["fields"]
        if isinstance(fields, list):
            values = {f["name"]: f["value"] for f in fields}
            if len(values) != len(fields):
                raise ValueError(f"custom format {data['name']!r}: duplicate condition fields")
            fields = values
        specifications[name] = {k: v for k, v in specification.items() if k not in {"name", "fields"}}
        specifications[name]["fields"] = fields
    return {"name": data["name"], "includeCustomFormatWhenRenaming": data["includeCustomFormatWhenRenaming"],
            "specifications": specifications}


def _differences(current: Any, desired: Any, field: str = "") -> list[dict[str, Any]]:
    if isinstance(current, dict) and isinstance(desired, dict):
        changes = []
        for key in sorted(current.keys() | desired.keys()):
            path = f"{field}.{key}" if field else key
            if field == "custom_format_scores":
                changes.extend(_differences(current.get(key, 0), desired.get(key, 0), path))
            elif key not in current or key not in desired:
                changes.append({"field": path, "current": current.get(key), "desired": desired.get(key)})
            else:
                changes.extend(_differences(current[key], desired[key], path))
        return changes
    if current != desired or type(current) is not type(desired):
        return [{"field": field or "$", "current": current, "desired": desired}]
    return []


def compare_profiles(
    source: Literal["radarr", "sonarr"], documents: Sequence[ProfileDocument],
    profiles: Sequence[dict[str, Any]], formats: Sequence[dict[str, Any]],
    selected: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Produce a deterministic read-only plan; no HTTP, filesystem, or persistent state."""
    validate_references(documents)
    names = select_profiles(source, documents, selected)
    report: dict[str, Any] = {"source": source, "profiles": names, "changes": [], "conflicts": []}
    if not names:
        return report
    desired_profiles = {
        p["name"]: p for d in documents if d.source == source and d.kind == "profiles"
        for p in d.data["quality_profiles"] if p["name"] in names
    }
    dependencies = {name for p in desired_profiles.values() for name in p["custom_format_scores"]}
    desired_formats = {
        d.data["name"]: d.data for d in documents
        if d.source == source and d.kind == "custom_formats" and d.data["name"] in dependencies
    }
    current_profiles = {p["name"]: p for p in profiles}
    if len(current_profiles) != len(profiles):
        raise ValueError("duplicate remote profile names")
    current_formats = {f["name"]: f for f in formats}
    format_ids = {f["id"]: f for f in formats}
    if len(current_formats) != len(formats) or len(format_ids) != len(formats):
        raise ValueError("duplicate remote custom format names or IDs")
    for name in sorted(dependencies):
        desired = _format(desired_formats[name])
        raw = current_formats.get(name)
        current = _format(export_custom_format(source, raw).data) if raw is not None else None
        changes = _differences(current, desired)
        report["changes"].extend({"kind": "custom_format", "name": name, **change} for change in changes)
        if changes and raw is not None:
            affected = sorted(p["name"] for p in profiles if p["name"] not in names
                              and any(item["format"] == raw["id"] for item in p["formatItems"]))
            if affected:
                report["conflicts"].append({"kind": "custom_format", "name": name, "profiles": affected})
    for name in names:
        desired = _profile(desired_profiles[name], desired_profiles[name])
        current = None
        if name in current_profiles:
            document = export_quality_profile(source, current_profiles[name], format_ids)
            current = _profile(document.data["quality_profiles"][0], desired)
        report["changes"].extend({"kind": "profile", "name": name, **change}
                                 for change in _differences(current, desired))
    return report
