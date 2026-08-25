"""Tests for the app test-suite runner (the `ci test` logic).

Selection and tier resolution are pure. :class:`AppSuites` is driven through
fakes, so these assert on the argv it *would* have run rather than running
pytest or npm.
"""

from __future__ import annotations

import json

import pytest

from conftest import ROOT, argvs, responds

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


class TestAppSuitesDiscovery:
    """`AppSuites` — which projects it finds, and which it refuses to."""

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


class TestAppSuitesPythonRuns:
    """`AppSuites.run_python` — what it invokes, and what it reports."""

    PROJECT = "stacks/apps/warden/app"

    @pytest.fixture
    def subject(self, container, filesystem):
        for tier in ("unit", "integration"):
            filesystem.files[f"{self.PROJECT}/tests/{tier}/test_x.py"] = ""
        return container.suites()

    def test_existing_tiers_run_in_one_pytest_call_keeping_addopts(self, subject, commands):
        rc, ran = subject.run_python([self.PROJECT], ["unit", "integration", "e2e"], gated=True)
        assert (rc, ran) == (0, True)
        assert argvs(commands) == [["uv", "run", "pytest", "tests/unit", "tests/integration"]]

    def test_the_run_happens_in_the_project_directory(self, subject, commands):
        subject.run_python([self.PROJECT], ["unit"])
        assert commands.run.call_args_list[0].kwargs["cwd"].as_posix().endswith(self.PROJECT)

    def test_an_ungated_run_clears_addopts(self, subject, commands):
        subject.run_python([self.PROJECT], ["unit"], gated=False)
        assert argvs(commands) == [["uv", "run", "pytest", "tests/unit", "-o", "addopts="]]

    def test_a_project_with_no_matching_tier_runs_nothing(self, subject, commands):
        rc, ran = subject.run_python([self.PROJECT], ["e2e"])
        assert (rc, ran) == (0, False)
        assert argvs(commands) == []

    def test_a_failing_suite_sets_the_exit_code(self, container, filesystem, commands):
        filesystem.files[f"{self.PROJECT}/tests/unit/test_x.py"] = ""
        commands.run.side_effect = [CommandResult(1)]
        rc, ran = container.suites().run_python([self.PROJECT], ["unit"])
        assert (rc, ran) == (1, True)

    def test_the_project_is_announced_before_it_runs(self, subject, caplog):
        subject.run_python([self.PROJECT], ["unit"])
        assert caplog.messages == [f"==> {self.PROJECT} : unit"]


class TestAppSuitesJsRuns:
    """`AppSuites.run_js` — npm ci then the tier's script, and the failure paths."""

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
        assert argvs(commands) == [["npm", "ci"], ["npm", "run", "test"]]

    def test_an_explicit_tier_runs_its_own_script(self, subject, commands):
        subject.run_js([self.PROJECT], "unit")
        assert argvs(commands)[-1] == ["npm", "run", "test:unit"]

    def test_a_tier_the_project_does_not_declare_is_skipped(self, subject, commands):
        rc, ran = subject.run_js([self.PROJECT], "e2e")
        assert (rc, ran) == (0, False)
        assert argvs(commands) == []

    def test_a_failed_install_skips_the_test_run(self, subject, commands):
        commands.run.side_effect = [CommandResult(1)]
        rc, ran = subject.run_js([self.PROJECT], None)
        assert (rc, ran) == (1, True)
        assert argvs(commands) == [["npm", "ci"]]


class TestSuiteRunner:
    """`SuiteRunner` — the whole `ci test` decision, moved out of the CLI handler."""

    PY = "stacks/apps/warden/app"
    BUILDABLE = (
        "services:\n  warden:\n    image: ghcr.io/ns/warden:1.0.0\n"
        "    build: { context: ., dockerfile: Dockerfile }\n"
    )

    @pytest.fixture
    def subject(self, container, filesystem):
        filesystem.files[f"{self.PY}/pyproject.toml"] = "[project]\n"
        filesystem.files[f"{self.PY}/tests/unit/test_x.py"] = ""
        return container.suite_runner()

    def test_a_selector_narrows_to_that_project(self, subject, commands):
        assert subject.run(selector="warden") == 0
        assert argvs(commands) == [["uv", "run", "pytest", "tests/unit"]]

    def test_a_selector_matching_nothing_runs_nothing_and_says_so(
        self, subject, commands, caplog
    ):
        assert subject.run(selector="nope") == 0
        assert argvs(commands) == []
        assert "No matching test suites." in caplog.text

    def test_an_explicit_tier_clears_the_coverage_gate(self, subject, commands):
        subject.run(selector="warden", tier="unit")
        assert argvs(commands) == [["uv", "run", "pytest", "tests/unit", "-o", "addopts="]]

    def test_changed_files_come_from_the_diff_against_the_base(
        self, container, filesystem, commands
    ):
        responds(commands, CommandResult(0, "stacks/apps/warden/app/main.py\ndocs/x.md\n"))
        changed = container.suite_runner().changed_files("origin/main")
        assert changed == ["stacks/apps/warden/app/main.py", "docs/x.md"]
        assert argvs(commands)[0] == [
            "git", "-C", str(ROOT), "diff", "--name-only", "origin/main...HEAD"
        ]

    def test_a_project_is_affected_when_the_diff_edits_a_file_inside_it(self, subject):
        assert subject.affected_projects([self.PY], [f"{self.PY}/main.py"]) == [self.PY]

    def test_a_project_is_not_affected_by_an_unrelated_change(self, subject):
        assert subject.affected_projects([self.PY], ["docs/readme.md"]) == []

    def test_a_prefix_that_is_not_a_directory_boundary_does_not_count(self, subject):
        assert subject.affected_projects(["a/warden"], ["a/warden-other/x.py"]) == []

    def test_a_project_is_affected_through_the_build_context_it_sits_under(
        self, container, filesystem
    ):
        filesystem.files["stacks/apps/warden/docker-compose.yml"] = self.BUILDABLE
        runner = container.suite_runner()
        # main.py is under the warden build context, which the watch glob covers.
        assert runner.affected_projects([self.PY], ["stacks/apps/warden/app/main.py"]) == [self.PY]

    def test_a_project_that_builds_no_image_is_still_reached_by_a_path_edit(self, subject):
        assert subject.affected_projects(["tools/ci"], ["tools/ci/ci/stackgraph.py"]) == ["tools/ci"]

    def test_affected_mode_runs_only_the_changed_projects_suite(
        self, container, filesystem, commands
    ):
        filesystem.files["stacks/apps/warden/docker-compose.yml"] = self.BUILDABLE
        filesystem.files[f"{self.PY}/pyproject.toml"] = "[project]\n"
        filesystem.files[f"{self.PY}/tests/unit/test_x.py"] = ""
        filesystem.files["stacks/apps/fiber/app/pyproject.toml"] = "[project]\n"
        filesystem.files["stacks/apps/fiber/app/tests/unit/test_y.py"] = ""
        responds(commands, CommandResult(0, "stacks/apps/warden/app/main.py\n"))
        container.suite_runner().run(affected=True)
        assert argvs(commands)[1:] == [["uv", "run", "pytest", "tests/unit"]]

    def test_a_failing_python_suite_sets_the_exit_code(self, container, filesystem, commands):
        filesystem.files[f"{self.PY}/pyproject.toml"] = "[project]\n"
        filesystem.files[f"{self.PY}/tests/unit/test_x.py"] = ""
        responds(commands, CommandResult(1))
        assert container.suite_runner().run(selector="warden") == 1
