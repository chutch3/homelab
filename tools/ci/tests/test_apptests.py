"""Unit tests for the `ci test` runner logic (discovery, selection, tier handling)."""

from __future__ import annotations

import textwrap
from pathlib import Path

from ci.apptests import (
    discover_js_projects,
    discover_test_projects,
    js_script_for_tier,
    run_js_tests,
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
    rc, ran = run_tests(tmp_path, ["stacks/apps/warden/app"], ["unit", "integration", "e2e"],
                        gated=True, runner=_fake_runner(calls))
    assert len(calls) == 1  # one combined invocation
    cmd = calls[0][0]
    assert cmd[:3] == ["uv", "run", "pytest"]
    assert "tests/unit" in cmd and "tests/integration" in cmd and "tests/e2e" not in cmd
    assert "-o" not in cmd  # gated → keep the project's addopts (coverage on the combined run)
    assert rc == 0 and ran is True


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
    rc, ran = run_tests(tmp_path, ["stacks/apps/warden/app"], ["unit"],
                        runner=_fake_runner([], returncode=1))
    assert rc == 1 and ran is True


def test_run_tests_reports_nothing_ran_when_no_tiers(tmp_path):
    (tmp_path / "stacks/apps/warden/app").mkdir(parents=True)  # no tests/ dirs
    rc, ran = run_tests(tmp_path, ["stacks/apps/warden/app"], ["unit"], runner=_fake_runner([]))
    assert rc == 0 and ran is False


# ---------------------------------------------------------------------------
# JavaScript projects (package.json with an npm test script) — vitest, etc.
# ---------------------------------------------------------------------------

def test_js_script_for_tier():
    assert js_script_for_tier(None) == "test"  # gated default suite
    assert js_script_for_tier("unit") == "test:unit"
    assert js_script_for_tier("e2e") == "test:e2e"


def test_discover_js_projects_wants_a_test_script_and_skips_node_modules(tmp_path):
    app = tmp_path / "stacks/apps/beholder/app"
    app.mkdir(parents=True)
    (app / "package.json").write_text('{"scripts": {"test": "vitest run"}}')
    # a package.json with no test script is not a JS test project
    plain = tmp_path / "stacks/apps/plain/app"
    plain.mkdir(parents=True)
    (plain / "package.json").write_text('{"scripts": {"start": "node ."}}')
    # vendored package.json under node_modules must be ignored
    nm = app / "node_modules" / "dep"
    nm.mkdir(parents=True)
    (nm / "package.json").write_text('{"scripts": {"test": "x"}}')
    assert discover_js_projects(tmp_path) == ["stacks/apps/beholder/app"]


def test_run_js_tests_installs_then_runs_the_default_script(tmp_path):
    app = tmp_path / "stacks/apps/beholder/app"
    app.mkdir(parents=True)
    (app / "package.json").write_text('{"scripts": {"test": "vitest run"}}')
    calls: list = []
    rc, ran = run_js_tests(tmp_path, ["stacks/apps/beholder/app"], None, runner=_fake_runner(calls))
    assert rc == 0 and ran is True
    assert [c[0] for c in calls] == [["npm", "ci"], ["npm", "run", "test"]]
    assert calls[0][1].endswith("stacks/apps/beholder/app")  # run in the project dir


def test_run_js_tests_uses_the_tier_script_when_present(tmp_path):
    app = tmp_path / "stacks/apps/beholder/app"
    app.mkdir(parents=True)
    (app / "package.json").write_text(
        '{"scripts": {"test": "x", "test:unit": "vitest run tests/unit"}}')
    calls: list = []
    run_js_tests(tmp_path, ["stacks/apps/beholder/app"], "unit", runner=_fake_runner(calls))
    assert ["npm", "run", "test:unit"] in [c[0] for c in calls]


def test_run_js_tests_skips_project_without_the_tier_script(tmp_path):
    app = tmp_path / "stacks/apps/fiber/app"
    app.mkdir(parents=True)
    (app / "package.json").write_text('{"scripts": {"test": "vitest run"}}')  # no test:e2e
    calls: list = []
    rc, ran = run_js_tests(tmp_path, ["stacks/apps/fiber/app"], "e2e", runner=_fake_runner(calls))
    assert rc == 0 and ran is False and calls == []


def test_run_js_tests_propagates_failure(tmp_path):
    app = tmp_path / "stacks/apps/beholder/app"
    app.mkdir(parents=True)
    (app / "package.json").write_text('{"scripts": {"test": "vitest run"}}')
    rc, ran = run_js_tests(tmp_path, ["stacks/apps/beholder/app"], None,
                           runner=_fake_runner([], returncode=1))
    assert rc == 1
