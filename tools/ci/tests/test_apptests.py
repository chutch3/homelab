"""Tests for the app test-suite runner (the `ci test` logic).

Selection and tier resolution are pure. :class:`TestSuites` is driven through
fakes, so these assert on the argv it *would* have run rather than running
pytest or npm.
"""

from __future__ import annotations

import json

import pytest

from ci.adapters import CommandResult
from ci.apptests import js_script_for_tier, select_projects, tiers_to_run

PROJECTS = ["stacks/apps/warden/app", "stacks/apps/fiber/app", "stacks/apps/fiber/ui"]


def test_select_by_bare_name_matches_path_segment():
    assert select_projects(PROJECTS, "warden") == ["stacks/apps/warden/app"]


def test_select_by_path_prefix():
    assert select_projects(PROJECTS, "stacks/apps/fiber") == [
        "stacks/apps/fiber/app",
        "stacks/apps/fiber/ui",
    ]


def test_select_empty_selector_returns_all():
    assert select_projects(PROJECTS, None) == PROJECTS
    assert select_projects(PROJECTS, "") == PROJECTS


def test_select_no_match_returns_empty():
    assert select_projects(PROJECTS, "nope") == []


def test_tiers_to_run():
    assert tiers_to_run(None) == ["unit", "integration"]
    assert tiers_to_run("e2e") == ["e2e"]
    with pytest.raises(ValueError, match="unknown tier"):
        tiers_to_run("smoke")


def test_js_script_for_tier():
    assert js_script_for_tier(None) == "test"
    assert js_script_for_tier("unit") == "test:unit"


class TestSuitesDiscovery:
    """`TestSuites` — which projects it finds, and which it refuses to."""

    @pytest.fixture
    def subject(self, container):
        return container.suites()

    def test_finds_pyproject_dirs(self, subject, filesystem):
        filesystem.files["stacks/apps/warden/app/pyproject.toml"] = "[project]\nname='warden'\n"
        assert subject.python_projects() == ["stacks/apps/warden/app"]

    def test_skips_pyproject_inside_a_venv(self, subject, filesystem):
        filesystem.files["stacks/apps/warden/app/pyproject.toml"] = "[project]\n"
        filesystem.files["stacks/apps/warden/app/.venv/lib/dep/pyproject.toml"] = "[project]\n"
        assert subject.python_projects() == ["stacks/apps/warden/app"]

    def test_finds_js_projects_declaring_a_test_script(self, subject, filesystem):
        filesystem.files["stacks/apps/fiber/ui/package.json"] = json.dumps(
            {"scripts": {"test": "vitest run"}}
        )
        assert subject.js_projects() == ["stacks/apps/fiber/ui"]

    def test_skips_js_projects_without_a_test_script(self, subject, filesystem):
        filesystem.files["stacks/apps/fiber/ui/package.json"] = json.dumps(
            {"scripts": {"build": "vite build"}}
        )
        assert subject.js_projects() == []

    def test_skips_package_json_inside_node_modules(self, subject, filesystem):
        filesystem.files["stacks/apps/fiber/ui/package.json"] = json.dumps(
            {"scripts": {"test": "vitest run"}}
        )
        filesystem.files["stacks/apps/fiber/ui/node_modules/dep/package.json"] = json.dumps(
            {"scripts": {"test": "x"}}
        )
        assert subject.js_projects() == ["stacks/apps/fiber/ui"]


class TestSuitesPythonRuns:
    """`TestSuites.run_python` — what it invokes, and what it reports."""

    PROJECT = "stacks/apps/warden/app"

    @pytest.fixture
    def subject(self, container, filesystem):
        for tier in ("unit", "integration"):
            filesystem.files[f"{self.PROJECT}/tests/{tier}/test_x.py"] = ""
        return container.suites()

    def test_existing_tiers_run_in_one_pytest_call_keeping_addopts(self, subject, commands):
        rc, ran = subject.run_python([self.PROJECT], ["unit", "integration", "e2e"], gated=True)
        assert (rc, ran) == (0, True)
        assert commands.argvs == [["uv", "run", "pytest", "tests/unit", "tests/integration"]]

    def test_the_run_happens_in_the_project_directory(self, subject, commands):
        subject.run_python([self.PROJECT], ["unit"])
        assert commands.calls[0]["cwd"].as_posix().endswith(self.PROJECT)

    def test_an_ungated_run_clears_addopts(self, subject, commands):
        subject.run_python([self.PROJECT], ["unit"], gated=False)
        assert commands.argvs == [["uv", "run", "pytest", "tests/unit", "-o", "addopts="]]

    def test_a_project_with_no_matching_tier_runs_nothing(self, subject, commands):
        rc, ran = subject.run_python([self.PROJECT], ["e2e"])
        assert (rc, ran) == (0, False)
        assert commands.argvs == []

    def test_a_failing_suite_sets_the_exit_code(self, container, filesystem, commands):
        filesystem.files[f"{self.PROJECT}/tests/unit/test_x.py"] = ""
        commands._results = [CommandResult(1)]
        rc, ran = container.suites().run_python([self.PROJECT], ["unit"])
        assert (rc, ran) == (1, True)

    def test_the_project_is_announced_before_it_runs(self, subject, console):
        subject.run_python([self.PROJECT], ["unit"])
        assert console.stdout == [f"==> {self.PROJECT} : unit"]


class TestSuitesJsRuns:
    """`TestSuites.run_js` — npm ci then the tier's script, and the failure paths."""

    PROJECT = "stacks/apps/fiber/ui"

    @pytest.fixture
    def subject(self, container, filesystem):
        filesystem.files[f"{self.PROJECT}/package.json"] = json.dumps(
            {"scripts": {"test": "vitest run", "test:unit": "vitest run unit"}}
        )
        return container.suites()

    def test_installs_then_runs_the_default_script(self, subject, commands):
        rc, ran = subject.run_js([self.PROJECT], None)
        assert (rc, ran) == (0, True)
        assert commands.argvs == [["npm", "ci"], ["npm", "run", "test"]]

    def test_an_explicit_tier_runs_its_own_script(self, subject, commands):
        subject.run_js([self.PROJECT], "unit")
        assert commands.argvs[-1] == ["npm", "run", "test:unit"]

    def test_a_tier_the_project_does_not_declare_is_skipped(self, subject, commands):
        rc, ran = subject.run_js([self.PROJECT], "e2e")
        assert (rc, ran) == (0, False)
        assert commands.argvs == []

    def test_a_failed_install_skips_the_test_run(self, subject, commands):
        commands._results = [CommandResult(1)]
        rc, ran = subject.run_js([self.PROJECT], None)
        assert (rc, ran) == (1, True)
        assert commands.argvs == [["npm", "ci"]]
