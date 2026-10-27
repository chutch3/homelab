from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from warden.profiles.models import ProfileDocument


@dataclass(frozen=True)
class CommandOutput:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


def render_diff(report: dict[str, Any], as_json: bool = False) -> CommandOutput:
    changes, conflicts = report["changes"], report["conflicts"]
    status = 1 if conflicts else (2 if changes else 0)
    if as_json:
        return CommandOutput(json.dumps(report, ensure_ascii=False, indent=2) + "\n", exit_code=status)
    if not report["profiles"]:
        lines = [f"{report['source']}: profile comparison disabled."]
    elif not changes:
        count = len(report["profiles"])
        lines = [f"{report['source']}: no differences ({count} profile{'s' if count != 1 else ''})."]
    else:
        resources = len({(change["kind"], change["name"]) for change in changes})
        lines = [f"{report['source']}: {len(changes)} change{'s' if len(changes) != 1 else ''} "
                 f"across {resources} resource{'s' if resources != 1 else ''}."]
        for change in changes:
            current = json.dumps(change["current"], ensure_ascii=False, sort_keys=True)
            desired = json.dumps(change["desired"], ensure_ascii=False, sort_keys=True)
            lines.append(f"  {change['kind']} {json.dumps(change['name'])}: {change['field']}: {current} -> {desired}")
        for conflict in conflicts:
            lines.append(f"  conflict: custom_format {json.dumps(conflict['name'])} also used by unselected profiles: "
                         + ", ".join(json.dumps(name) for name in conflict["profiles"]))
    return CommandOutput("\n".join(lines) + "\n", exit_code=status)


def render_summary(command: str, documents: Sequence[ProfileDocument]) -> CommandOutput:
    profiles = sum(len(document.data["quality_profiles"]) for document in documents if document.kind == "profiles")
    formats = sum(document.kind == "custom_formats" for document in documents)
    if command == "dump":
        return CommandOutput(f"Exported {profiles} profiles and {formats} custom formats.\n")
    return CommandOutput(f"Valid configuration: {profiles} profiles, {formats} custom formats.\n")


def render_error(message: str) -> CommandOutput:
    return CommandOutput(stderr=f"error: {message}\n", exit_code=1)
