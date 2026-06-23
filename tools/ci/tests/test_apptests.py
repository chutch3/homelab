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
    assert tiers_to_run(None) == ["unit", "integration"]  # default gated suite
    assert tiers_to_run("unit") == ["unit"]
    assert tiers_to_run("e2e") == ["e2e"]
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


def _fake_runner(calls, returncode=0):
    def runner(cmd, cwd=None):
        calls.append((cmd, str(cwd)))

        class R:
            pass

        R.returncode = returncode
        return R()

    return runner


def test_gated_run_combines_existing_tiers_in_one_call_keeping_addopts(tmp_path):
    proj = tmp_path / "stacks/apps/warden/app"
    (proj / "tests" / "unit").mkdir(parents=True)
    (proj / "tests" / "integration").mkdir(parents=True)
    # no tests/e2e → excluded
    calls: list = []
    rc = run_tests(tmp_path, ["stacks/apps/warden/app"], ["unit", "integration", "e2e"],
                   gated=True, runner=_fake_runner(calls))
    assert len(calls) == 1  # one combined invocation
    cmd = calls[0][0]
    assert cmd[:3] == ["uv", "run", "pytest"]
    assert "tests/unit" in cmd and "tests/integration" in cmd and "tests/e2e" not in cmd
    assert "-o" not in cmd  # gated → keep the project's addopts (coverage on the combined run)
    assert rc == 0


def test_ungated_run_clears_addopts(tmp_path):
    proj = tmp_path / "stacks/apps/warden/app"
    (proj / "tests" / "integration").mkdir(parents=True)
    calls: list = []
    run_tests(tmp_path, ["stacks/apps/warden/app"], ["integration"], gated=False,
              runner=_fake_runner(calls))
    cmd = calls[0][0]
    assert "-o" in cmd and "addopts=" in cmd  # partial run → no coverage gate


def test_run_tests_propagates_failure(tmp_path):
    proj = tmp_path / "stacks/apps/warden/app"
    (proj / "tests" / "unit").mkdir(parents=True)
    rc = run_tests(tmp_path, ["stacks/apps/warden/app"], ["unit"],
                   runner=_fake_runner([], returncode=1))
    assert rc == 1
