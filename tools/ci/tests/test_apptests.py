"""Unit tests for the `ci test` runner logic (discovery, selection, tier handling)."""

from __future__ import annotations

import textwrap
from pathlib import Path

from ci.apptests import (
    discover_test_projects,
    run_tests,
    select_projects,
    tiers_to_run,
)

PROJECTS = [
    "stacks/apps/warden/app",
    "stacks/apps/takeout-manager/manager",
    "stacks/apps/takeout-manager/worker",
    "stacks/monitoring/custom-exporter",
]


def test_select_by_bare_name_matches_path_segment():
    assert select_projects(PROJECTS, "warden") == ["stacks/apps/warden/app"]
    assert select_projects(PROJECTS, "custom-exporter") == ["stacks/monitoring/custom-exporter"]


def test_select_by_path_prefix():
    # A context path selects projects at or under it (manager, not worker).
    assert select_projects(PROJECTS, "stacks/apps/takeout-manager/manager") == [
        "stacks/apps/takeout-manager/manager"
    ]
    # A broader path prefix selects everything under it.
    assert select_projects(PROJECTS, "stacks/apps/takeout-manager") == [
        "stacks/apps/takeout-manager/manager",
        "stacks/apps/takeout-manager/worker",
    ]


def test_select_empty_selector_returns_all():
    assert select_projects(PROJECTS, None) == PROJECTS


def test_select_no_match_returns_empty():
    assert select_projects(PROJECTS, "does-not-exist") == []


def test_tiers_to_run():
    assert tiers_to_run("all") == ["unit", "integration", "e2e"]
    assert tiers_to_run("unit") == ["unit"]
    import pytest

    with pytest.raises(ValueError):
        tiers_to_run("bogus")


def test_discover_finds_pyproject_dirs_and_skips_venv(tmp_path):
    (tmp_path / "stacks/apps/warden/app").mkdir(parents=True)
    (tmp_path / "stacks/apps/warden/app/pyproject.toml").write_text("[project]\nname='warden'\n")
    venv = tmp_path / "stacks/apps/warden/app/.venv/lib"
    venv.mkdir(parents=True)
    (venv / "pyproject.toml").write_text("")  # must be ignored
    assert discover_test_projects(tmp_path) == ["stacks/apps/warden/app"]


def _fake_runner(calls, rc_for=None):
    def runner(cmd, cwd=None):
        calls.append((cmd, str(cwd)))

        class R:
            returncode = (rc_for or {}).get(cmd[-1], 0)

        return R()

    return runner


def test_run_tests_skips_missing_tiers_and_clears_addopts_for_nonunit(tmp_path):
    proj = tmp_path / "stacks/apps/warden/app"
    (proj / "tests" / "unit").mkdir(parents=True)
    (proj / "tests" / "integration").mkdir(parents=True)
    # no tests/e2e → that tier is skipped
    calls: list = []
    rc = run_tests(tmp_path, ["stacks/apps/warden/app"], ["unit", "integration", "e2e"],
                   runner=_fake_runner(calls))
    invoked_tiers = [cmd[3] for cmd, _ in calls]  # "tests/<tier>"
    assert invoked_tiers == ["tests/unit", "tests/integration"]
    # unit keeps the project's addopts; integration clears them
    assert "-o" not in calls[0][0]
    assert "-o" in calls[1][0] and "addopts=" in calls[1][0]
    assert rc == 0


def test_run_tests_propagates_failure(tmp_path):
    proj = tmp_path / "stacks/apps/warden/app"
    (proj / "tests" / "unit").mkdir(parents=True)
    calls: list = []
    rc = run_tests(tmp_path, ["stacks/apps/warden/app"], ["unit"],
                   runner=_fake_runner(calls, rc_for={"tests/unit": 1}))
    assert rc == 1
