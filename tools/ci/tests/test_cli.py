"""Tests for the `ci` command surface.

This is the contract callers actually depend on: argv in, exit code and output
out. Every handler resolves its collaborators from the container, so these run
against fakes — nothing here touches the filesystem or spawns a process.
"""

from __future__ import annotations

import json

import pytest

from conftest import ROOT, argvs, responds

from ci.adapters import CommandResult
from ci.cli import build_parser

TRAEFIK = 'services:\n    a:\n        deploy:\n            labels: ["traefik.enable=true"]\n'
DECLARED = "x-homelab:\n    requires: [reverse-proxy]\n" + TRAEFIK
BUILDABLE = (
    "services:\n  warden:\n    image: ghcr.io/ns/warden:1.0.0\n"
    "    build: { context: ., dockerfile: Dockerfile }\n"
)


@pytest.fixture
def run(container):
    """Parse an argv and invoke its handler against the fake-wired container."""
    container.wire(modules=["ci.cli"])

    def _run(*argv: str) -> int:
        args = build_parser().parse_args(list(argv))
        return args.func(args)

    yield _run
    container.unwire()


class TestParser:
    """`build_parser` — the argv contract, before any handler runs."""

    def test_deploy_refuses_to_run_without_plan(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["deploy", "paperless"])

    def test_deploy_accepts_targets_with_plan(self):
        args = build_parser().parse_args(["deploy", "paperless", "komga", "--plan"])
        assert args.stacks == ["paperless", "komga"]

    def test_an_unknown_subcommand_is_rejected(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["nope"])

    def test_a_missing_subcommand_is_rejected(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args([])

    def test_idempotence_passes_ansible_flags_through_unparsed(self):
        args = build_parser().parse_args(
            ["idempotence", "play.yml", "-i", "inv/", "--skip-tags", "ssh"]
        )
        assert args.ansible_args == ["-i", "inv/", "--skip-tags", "ssh"]


class TestDeployCommand:
    """`ci deploy --plan` — prints an order, deploys nothing."""

    def test_prints_the_resolved_order_one_stack_per_line(self, run, filesystem, console):
        filesystem.files.update({
            "stacks/apps/paperless/docker-compose.yml": DECLARED,
            "stacks/reverse-proxy/docker-compose.yml": "services: {}\n",
        })
        assert run("deploy", "--plan") == 0
        assert console.stdout == ["reverse-proxy", "paperless"]

    def test_reports_the_count_on_stderr_so_stdout_stays_pipeable(
        self, run, filesystem, console
    ):
        filesystem.files["stacks/reverse-proxy/docker-compose.yml"] = "services: {}\n"
        run("deploy", "--plan")
        assert console.stdout == ["reverse-proxy"]
        assert "1 stack(s) — plan only, nothing deployed." in "\n".join(console.stderr)

    def test_a_target_narrows_the_plan_to_its_closure(self, run, filesystem, console):
        filesystem.files.update({
            "stacks/apps/paperless/docker-compose.yml": DECLARED,
            "stacks/apps/komga/docker-compose.yml": DECLARED,
            "stacks/reverse-proxy/docker-compose.yml": "services: {}\n",
        })
        assert run("deploy", "paperless", "--plan") == 0
        assert console.stdout == ["reverse-proxy", "paperless"]

    def test_an_unresolvable_graph_exits_one_and_explains_on_stderr(
        self, run, filesystem, console
    ):
        filesystem.files["stacks/apps/paperless/docker-compose.yml"] = (
            "x-homelab:\n    requires: [ghost-stack]\nservices: {}\n"
        )
        assert run("deploy", "--plan") == 1
        assert console.stdout == []
        assert "paperless requires ghost-stack" in "\n".join(console.stderr)

    def test_it_never_runs_a_command(self, run, filesystem, commands):
        filesystem.files["stacks/reverse-proxy/docker-compose.yml"] = "services: {}\n"
        run("deploy", "--plan")
        assert argvs(commands) == []


class TestCheckDepsCommand:
    """`ci check-deps` — the pre-commit hook's entry point."""

    def test_a_clean_tree_passes_and_reports_the_count(self, run, filesystem, console):
        filesystem.files.update({
            "stacks/apps/paperless/docker-compose.yml": DECLARED,
            "stacks/reverse-proxy/docker-compose.yml": "services: {}\n",
        })
        assert run("check-deps") == 0
        assert console.text.startswith("✓ 2 stacks resolve")

    def test_an_undeclared_dependency_exits_one_naming_the_stack(
        self, run, filesystem, console
    ):
        filesystem.files.update({
            "stacks/apps/komga/docker-compose.yml": TRAEFIK,
            "stacks/reverse-proxy/docker-compose.yml": "services: {}\n",
        })
        assert run("check-deps") == 1
        assert "    komga: reverse-proxy" in console.text

    def test_a_malformed_declaration_exits_one_explaining_the_shape(
        self, run, filesystem, console
    ):
        filesystem.files["stacks/apps/paperless/docker-compose.yml"] = (
            "x-homelab:\n    requires: reverse-proxy\nservices: {}\n"
        )
        assert run("check-deps") == 1
        assert "x-homelab.requires must be a list" in console.text

    def test_a_dangling_edge_from_a_deleted_stack_exits_one(self, run, filesystem, console):
        filesystem.files["stacks/apps/gamarr/docker-compose.yml"] = (
            "x-homelab:\n    requires: [romm]\nservices: {}\n"
        )
        assert run("check-deps") == 1
        assert "gamarr requires romm" in console.text


class TestAffectedCommand:
    """`ci affected` — the build matrix, as JSON on stdout."""

    def test_emits_json_for_the_affected_units(self, run, filesystem, console):
        filesystem.files["stacks/apps/warden/docker-compose.yml"] = BUILDABLE
        assert run("affected", ".", "stacks/apps/warden/app/main.py") == 0
        assert [e["image_name"] for e in json.loads(console.text)] == ["warden"]

    def test_an_unrelated_change_emits_an_empty_matrix(self, run, filesystem, console):
        filesystem.files["stacks/apps/warden/docker-compose.yml"] = BUILDABLE
        assert run("affected", ".", "docs/readme.md") == 0
        assert json.loads(console.text) == []


class TestImagesCommand:
    """`ci images` — one buildable image name per line."""

    def test_lists_every_image_once(self, run, filesystem, console):
        filesystem.files["stacks/apps/warden/docker-compose.yml"] = BUILDABLE
        assert run("images") == 0
        assert console.stdout == ["warden"]


class TestGcCommand:
    """`ci gc` — dry-run unless told otherwise."""

    def test_defaults_to_a_dry_run(self, run, filesystem, commands, console):
        filesystem.files["stacks/apps/warden/docker-compose.yml"] = BUILDABLE
        responds(commands, *[CommandResult(0, "[]")])
        assert run("gc") == 0
        assert console.stdout[-1] == "Would prune 0 version(s)."
        assert all("DELETE" not in a for argv in argvs(commands) for a in argv)


class TestTestCommand:
    """`ci test` — selection and the suites it invokes."""

    def test_no_matching_suite_says_so_and_still_succeeds(self, run, console):
        assert run("test") == 0
        assert "No matching test suites." in console.text

    def test_runs_the_gated_default_suite_for_a_selected_app(self, run, filesystem, commands):
        filesystem.files["stacks/apps/warden/app/pyproject.toml"] = "[project]\n"
        filesystem.files["stacks/apps/warden/app/tests/unit/test_x.py"] = ""
        assert run("test", "warden") == 0
        assert argvs(commands) == [["uv", "run", "pytest", "tests/unit"]]

    def test_an_explicit_tier_clears_addopts(self, run, filesystem, commands):
        filesystem.files["stacks/apps/warden/app/pyproject.toml"] = "[project]\n"
        filesystem.files["stacks/apps/warden/app/tests/unit/test_x.py"] = ""
        run("test", "warden", "--tier", "unit")
        assert argvs(commands) == [["uv", "run", "pytest", "tests/unit", "-o", "addopts="]]

    def test_affected_mode_asks_git_for_the_diff_range(self, run, filesystem, commands):
        filesystem.files["stacks/apps/warden/docker-compose.yml"] = BUILDABLE
        responds(commands, *[CommandResult(0, "stacks/apps/warden/app/main.py\n")])
        run("test", "--affected", "--base", "origin/main")
        assert argvs(commands)[0] == [
            "git", "-C", str(ROOT), "diff", "--name-only", "origin/main...HEAD"
        ]


class TestIdempotenceCommand:
    """`ci idempotence` — the exit code is the verdict."""

    def test_a_converged_playbook_exits_zero(self, run, commands):
        recap = (
            "PLAY RECAP ****\n"
            "node-01                    : ok=3    changed=0    unreachable=0    failed=0\n"
        )
        responds(commands, *[CommandResult(0, recap), CommandResult(0, recap)])
        assert run("idempotence", "play.yml") == 0

    def test_a_drifting_playbook_exits_one(self, run, commands):
        recap = (
            "PLAY RECAP ****\n"
            "node-01                    : ok=3    changed=2    unreachable=0    failed=0\n"
        )
        responds(commands, *[CommandResult(0, recap), CommandResult(0, recap)])
        assert run("idempotence", "play.yml") == 1
