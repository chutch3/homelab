from __future__ import annotations

import json

import pytest

from warden.profiles.models import ProfileDocument
from warden.cli_output import CommandOutput, render_diff, render_error, render_summary


def report(profiles: list[str], changes: list[dict] | None = None, conflicts: list[dict] | None = None) -> dict:
    return {"source": "radarr", "profiles": profiles, "changes": changes or [], "conflicts": conflicts or []}


def test_disabled_comparison() -> None:
    assert render_diff(report([])) == CommandOutput("radarr: profile comparison disabled.\n")


@pytest.mark.parametrize("profiles,expected", [(["HD"], "1 profile"), (["HD", "UHD"], "2 profiles")])
def test_clean_comparison(profiles: list[str], expected: str) -> None:
    assert render_diff(report(profiles)) == CommandOutput(f"radarr: no differences ({expected}).\n")


def test_changes_count_resources_and_format_values() -> None:
    changes = [
        {"kind": "profile", "name": "HD", "field": "score", "current": 100, "desired": 250},
        {"kind": "profile", "name": "HD", "field": "enabled", "current": False, "desired": True},
    ]
    assert render_diff(report(["HD"], changes)) == CommandOutput(
        'radarr: 2 changes across 1 resource.\n'
        '  profile "HD": score: 100 -> 250\n'
        '  profile "HD": enabled: false -> true\n', exit_code=2,
    )


def test_conflicts_take_precedence_over_drift_exit_code() -> None:
    changes = [{"kind": "custom_format", "name": "Preferred", "field": "$", "current": None, "desired": {"value": "new"}}]
    conflicts = [{"kind": "custom_format", "name": "Preferred", "profiles": ["Other"]}]
    assert render_diff(report(["HD"], changes, conflicts)) == CommandOutput(
        'radarr: 1 change across 1 resource.\n'
        '  custom_format "Preferred": $: null -> {"value": "new"}\n'
        '  conflict: custom_format "Preferred" also used by unselected profiles: "Other"\n', exit_code=1,
    )


@pytest.mark.parametrize("changed,conflicted,status", [(False, False, 0), (True, False, 2), (True, True, 1)])
def test_json_preserves_report_and_exit_status(changed: bool, conflicted: bool, status: int) -> None:
    value = report(["HD"], [{"name": "HD"}] if changed else [], [{"name": "Shared"}] if conflicted else [])
    result = render_diff(value, as_json=True)
    assert json.loads(result.stdout) == value
    assert result.stdout.endswith("\n")
    assert result.stderr == ""
    assert result.exit_code == status


@pytest.mark.parametrize("command,prefix", [("dump", "Exported"), ("validate", "Valid configuration:")])
def test_catalog_summary(command: str, prefix: str) -> None:
    documents = [ProfileDocument("radarr", "profiles", "profiles.yml", {"quality_profiles": [{}, {}]})]
    separator = " and" if command == "dump" else ","
    assert render_summary(command, documents) == CommandOutput(f"{prefix} 2 profiles{separator} 0 custom formats.\n")


def test_error_uses_stderr_and_failure_status() -> None:
    assert render_error("catalog invalid") == CommandOutput(stderr="error: catalog invalid\n", exit_code=1)
