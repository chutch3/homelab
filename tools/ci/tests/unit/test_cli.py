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
from ci.cli import build_container, build_parser

TRAEFIK = 'services:\n    a:\n        deploy:\n            labels: ["traefik.enable=true"]\n'
DECLARED = "x-homelab:\n    requires: [reverse-proxy]\n" + TRAEFIK
HEALTHCHECK = '        healthcheck:\n            test: ["CMD", "true"]\n'
HEALTHY = 'services:\n    a:\n' + HEALTHCHECK
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


# Every subcommand's argv must be enough to wire the container — the composition
# root reads `--repo-root` off it, and nothing else checks that it is there.
SUBCOMMANDS = [
    ["affected"],
    ["projects"],
    ["images"],
    ["gc"],
    ["test"],
    ["idempotence", "play.yml"],
    ["plan"],
    ["check-stacks"],
]


@pytest.mark.parametrize("argv", SUBCOMMANDS, ids=lambda argv: argv[0])
def test_build_container_wires_every_subcommand(argv):
    container = build_container(build_parser().parse_args(argv), process_env={})
    try:
        assert container.repo_root() == "."
    finally:
        container.unwire()


# ── build_parser: the argv contract, before any handler runs ────────────────

def test_parser_plan_accepts_targets():
    args = build_parser().parse_args(["plan", "paperless", "komga"])
    assert args.stacks == ["paperless", "komga"]


def test_parser_plan_with_no_targets_means_every_stack():
    assert build_parser().parse_args(["plan"]).stacks == []


def test_parser_idempotence_takes_repo_root_only_before_the_playbook():
    """REMAINDER swallows everything after it, the flag included."""
    before = build_parser().parse_args(["idempotence", "--repo-root", "/tmp", "play.yml"])
    assert (before.repo_root, before.ansible_args) == ("/tmp", [])

    after = build_parser().parse_args(["idempotence", "play.yml", "--repo-root", "/tmp"])
    assert (after.repo_root, after.ansible_args) == (".", ["--repo-root", "/tmp"])


def test_parser_rejects_an_unknown_subcommand():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["nope"])


def test_parser_rejects_a_missing_subcommand():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_parser_idempotence_passes_ansible_flags_through_unparsed():
    args = build_parser().parse_args(
        ["idempotence", "play.yml", "-i", "inv/", "--skip-tags", "ssh"]
    )
    assert args.ansible_args == ["-i", "inv/", "--skip-tags", "ssh"]


# ── ci plan ─────────────────────────────────────────────────────────────────
# What the plan *says* is `test_deploy.py`'s job. These assert only the wiring:
# the payload reaches stdout, and a failure's exit code propagates.

@pytest.fixture
def routed(filesystem):
    """A two-stack tree that resolves: paperless behind reverse-proxy."""
    filesystem.files.update({
        "stacks/apps/paperless/docker-compose.yml": DECLARED,
        "stacks/reverse-proxy/docker-compose.yml": "services: {}\n",
    })


def test_plan_prints_the_plan_and_exits_zero(run, routed, capsys):
    assert run("plan") == 0
    printed = capsys.readouterr().out
    assert [line.split()[1] for line in printed.splitlines()] == ["reverse-proxy", "paperless"]


def test_plan_json_prints_the_plan_the_playbook_parses(run, routed, capsys):
    assert run("plan", "--json") == 0
    assert [row["stack"] for row in json.loads(capsys.readouterr().out)] == [
        "reverse-proxy",
        "paperless",
    ]


def test_plan_propagates_a_failed_plans_exit_code(run, filesystem, capsys):
    filesystem.files["stacks/apps/paperless/docker-compose.yml"] = (
        "x-homelab:\n    requires: [ghost-stack]\nservices: {}\n"
    )
    assert run("plan") == 1
    assert capsys.readouterr().out == ""


# ── ci check-stacks ─────────────────────────────────────────────────────────
# The verdicts are `test_stackcheck.py`; these assert that argv reaches it and
# both exit codes come back.

def test_check_stacks_exits_zero_for_a_clean_tree(run, filesystem):
    filesystem.files.update({
        "stacks/apps/paperless/docker-compose.yml": DECLARED + HEALTHCHECK,
        "stacks/reverse-proxy/docker-compose.yml": HEALTHY,
    })
    assert run("check-stacks") == 0


def test_check_stacks_exits_one_for_a_tree_that_does_not_check_out(run, filesystem, caplog):
    filesystem.files["stacks/apps/gamarr/docker-compose.yml"] = (
        "x-homelab:\n    requires: [romm]\nservices: {}\n"
    )
    assert run("check-stacks") == 1
    assert "gamarr requires romm" in caplog.text


# ── ci affected: the build matrix, as JSON on stdout ────────────────────────

def test_affected_emits_json_for_the_affected_units(run, filesystem, capsys):
    filesystem.files["stacks/apps/warden/docker-compose.yml"] = BUILDABLE
    assert run("affected", ".", "stacks/apps/warden/app/main.py") == 0
    assert [e["image_name"] for e in json.loads(capsys.readouterr().out)] == ["warden"]


def test_affected_emits_an_empty_matrix_for_an_unrelated_change(run, filesystem, capsys):
    filesystem.files["stacks/apps/warden/docker-compose.yml"] = BUILDABLE
    assert run("affected", ".", "docs/readme.md") == 0
    assert json.loads(capsys.readouterr().out) == []


# ── ci images: one buildable image name per line ────────────────────────────

def test_images_lists_every_image_once(run, filesystem, capsys, caplog):
    filesystem.files["stacks/apps/warden/docker-compose.yml"] = BUILDABLE
    assert run("images") == 0
    assert capsys.readouterr().out.splitlines() == ["warden"]


# ── ci gc: dry-run unless told otherwise ────────────────────────────────────

def test_gc_defaults_to_a_dry_run(run, filesystem, commands, caplog):
    filesystem.files["stacks/apps/warden/docker-compose.yml"] = BUILDABLE
    responds(commands, *[CommandResult(0, "[]")])
    assert run("gc") == 0
    assert caplog.messages[-1] == "Would prune 0 version(s)."
    assert all("DELETE" not in a for argv in argvs(commands) for a in argv)


# ── ci test: selection and the suites it invokes ────────────────────────────

@pytest.fixture
def warden_suite(filesystem):
    filesystem.files["stacks/apps/warden/app/pyproject.toml"] = "[project]\n"
    filesystem.files["stacks/apps/warden/app/tests/unit/test_x.py"] = ""


def test_test_no_matching_suite_says_so_and_still_succeeds(run, caplog):
    assert run("test") == 0
    assert "No matching test suites." in caplog.text


def test_test_runs_the_gated_default_suite_for_a_selected_app(run, warden_suite, commands):
    assert run("test", "warden") == 0
    assert argvs(commands) == [["uv", "run", "pytest", "tests/unit"]]


def test_test_an_explicit_tier_clears_addopts(run, warden_suite, commands):
    run("test", "warden", "--tier", "unit")
    assert argvs(commands) == [["uv", "run", "pytest", "tests/unit", "-o", "addopts="]]


def test_test_affected_mode_asks_git_for_the_diff_range(run, filesystem, commands):
    filesystem.files["stacks/apps/warden/docker-compose.yml"] = BUILDABLE
    responds(commands, *[CommandResult(0, "stacks/apps/warden/app/main.py\n")])
    run("test", "--affected", "--base", "origin/main")
    assert argvs(commands)[0] == [
        "git", "-C", str(ROOT), "diff", "--name-only", "origin/main...HEAD"
    ]


# ── ci idempotence: the exit code is the verdict ────────────────────────────

def _recap(changed: int) -> str:
    return (
        "PLAY RECAP ****\n"
        f"node-01                    : ok=3    changed={changed}    unreachable=0    failed=0\n"
    )


def test_idempotence_a_converged_playbook_exits_zero(run, commands):
    responds(commands, *[CommandResult(0, _recap(0)), CommandResult(0, _recap(0))])
    assert run("idempotence", "play.yml") == 0


def test_idempotence_a_drifting_playbook_exits_one(run, commands):
    responds(commands, *[CommandResult(0, _recap(2)), CommandResult(0, _recap(2))])
    assert run("idempotence", "play.yml") == 1


# ── ci projects: the test matrix, sibling of `ci affected`'s build matrix ───

PY_PROJECT = "stacks/apps/warden/app"


@pytest.fixture
def project_tree(filesystem):
    filesystem.files.update({
        "stacks/apps/warden/docker-compose.yml": BUILDABLE,
        f"{PY_PROJECT}/pyproject.toml": "[project]\n",
        f"{PY_PROJECT}/tests/unit/test_x.py": "",
        "tools/ci/pyproject.toml": "[project]\n",
        "tools/ci/tests/unit/test_y.py": "",
    })


def _projects(capsys) -> list[str]:
    return [e["project"] for e in json.loads(capsys.readouterr().out)]


def test_projects_a_change_inside_a_project_selects_that_project(run, project_tree, capsys):
    assert run("projects", ".", f"{PY_PROJECT}/main.py") == 0
    assert _projects(capsys) == [PY_PROJECT]


def test_projects_a_change_to_the_ci_tooling_selects_the_ci_tooling(run, project_tree, capsys):
    assert run("projects", ".", "tools/ci/ci/stackgraph.py") == 0
    assert "tools/ci" in _projects(capsys)


def test_projects_an_unrelated_change_selects_nothing(run, project_tree, capsys):
    assert run("projects", ".", "docs/index.md") == 0
    assert _projects(capsys) == []


def test_projects_the_output_is_a_github_matrix_include_list(run, project_tree, capsys):
    run("projects", ".", f"{PY_PROJECT}/main.py")
    entries = json.loads(capsys.readouterr().out)
    assert entries == [{"project": PY_PROJECT}]


def test_projects_a_project_that_builds_no_image_is_reachable_only_by_path(
    run, project_tree, capsys
):
    # tools/ci has no compose unit, so nothing but a path edit can select it.
    run("projects", ".", f"{PY_PROJECT}/main.py")
    assert "tools/ci" not in _projects(capsys)
