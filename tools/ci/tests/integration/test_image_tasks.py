from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[4]


@pytest.fixture
def task_repo(tmp_path: Path) -> Path:
    for relative in ("Taskfile.yml", "ansible/Taskfile.yml", "tools/status-pipeline/Taskfile.yml"):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / relative, destination)
    (tmp_path / "stacks/apps/warden").mkdir(parents=True)
    shutil.copytree(REPO / "tools/dev", tmp_path / "tools/dev")
    binary = tmp_path / "bin/docker"
    binary.parent.mkdir()
    binary.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "print(json.dumps({'tag': os.environ.get('IMAGE_TAG'), 'args': sys.argv[1:], "
        "'directory': os.path.basename(os.getcwd())}))\n"
    )
    binary.chmod(0o755)
    (tmp_path / "bin/uv").symlink_to(shutil.which("uv"))
    return tmp_path


def invoke(root: Path, command: str, tag: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {"PATH": f"{root / 'bin'}{os.pathsep}{os.defpath}", "HOME": str(root), "GITHUB_USERNAME": "example"}
    env.update(UV_NO_SYNC="1", UV_PROJECT_ENVIRONMENT=str(REPO / ".venv"))
    if tag is not None:
        env["IMAGE_TAG"] = tag
    task = shutil.which("task")
    assert task, "Go Task is required for the image-task integration tests"
    return subprocess.run(
        [task, "--silent", "--dir", str(root), command, "--", "warden"],
        env=env, text=True, capture_output=True, timeout=30,
    )


@pytest.mark.parametrize("command", ["build", "publish"])
def test_explicit_image_tag_reaches_bake(task_repo: Path, command: str) -> None:
    result = invoke(task_repo, command, "3.36.0-dev.1")
    assert result.returncode == 0, result.stderr
    expected_args = ["buildx", "bake", "--allow", "fs.read=*", "-f", "docker-compose.yml"]
    if command == "publish":
        expected_args.append("--push")
    assert json.loads(result.stdout) == {"tag": "3.36.0-dev.1", "args": expected_args, "directory": "warden"}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def initialize(root: Path, message: str | None = "feat: add profiles", config: str = "", release_tag: str = "v1.2.3") -> str:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "1.2.3"\n'
        '[tool.semantic_release]\ncommit_parser = "conventional"\nmajor_on_zero = false\n' + config
    )
    git(root, "init", "-b", "feature/profiles")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "remote", "add", "origin", "https://github.com/example/fixture.git")
    git(root, "add", ".")
    git(root, "commit", "-m", "chore: initial release")
    git(root, "tag", release_tag)
    if message:
        git(root, "commit", "--allow-empty", "-m", message)
    return git(root, "rev-parse", "--short=12", "HEAD")


@pytest.mark.parametrize("command", ["build", "publish"])
@pytest.mark.parametrize("tag", [None, ""])
def test_missing_image_tag_uses_semantic_release(task_repo: Path, command: str, tag: str | None) -> None:
    sha = initialize(task_repo)
    before = (git(task_repo, "status", "--porcelain"), git(task_repo, "show-ref"), (task_repo / "pyproject.toml").read_bytes())
    result = invoke(task_repo, command, tag)
    assert result.returncode == 0, result.stderr
    actual = json.loads(result.stdout)
    assert re.fullmatch(rf"1\.3\.0-dev\.1\.t[0-9]+\.g{sha}", actual["tag"])
    assert ("--push" in actual["args"]) == (command == "publish")
    assert (git(task_repo, "status", "--porcelain"), git(task_repo, "show-ref"), (task_repo / "pyproject.toml").read_bytes()) == before


@pytest.mark.parametrize(("message", "version"), [
    ("fix: repair import", "1.2.4"),
    ("feat!: replace the profile schema", "2.0.0"),
    ("docs: explain profiles", "1.2.4"),
    (None, "1.2.4"),
])
def test_semantic_bumps_and_no_release_fallback(task_repo: Path, message: str | None, version: str) -> None:
    initialize(task_repo, message)
    result = invoke(task_repo, "publish")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["tag"].startswith(f"{version}-dev.1.")


def test_repository_semantic_release_options_are_respected(task_repo: Path) -> None:
    initialize(task_repo, "enhancement: add profiles", 'tag_format = "release-{version}"\n[tool.semantic_release.commit_parser_options]\nminor_tags = ["enhancement"]\nallowed_tags = ["enhancement", "chore"]\n', "release-1.2.3")
    result = invoke(task_repo, "publish")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["tag"].startswith("1.3.0-dev.1.")


def test_dirty_rebuilds_get_distinct_tags(task_repo: Path) -> None:
    sha = initialize(task_repo)
    (task_repo / "uncommitted.txt").write_text("work in progress")
    results = [invoke(task_repo, "publish"), invoke(task_repo, "publish")]
    for result in results:
        assert result.returncode == 0, result.stderr
        assert re.fullmatch(rf"1\.3\.0-dev\.1\.t[0-9]+\.g{sha}\.dirty", json.loads(result.stdout)["tag"])
    assert json.loads(results[0].stdout)["tag"] != json.loads(results[1].stdout)["tag"]


@pytest.mark.parametrize("command", ["build", "publish"])
def test_version_calculation_failure_does_not_invoke_docker(task_repo: Path, command: str) -> None:
    result = invoke(task_repo, command)
    assert result.returncode != 0
    assert result.stderr
    assert result.stdout == ""


def test_preview_prints_the_resolved_tag_without_docker(task_repo: Path) -> None:
    sha = initialize(task_repo)
    result = invoke(task_repo, "image:tag")
    assert result.returncode == 0, result.stderr
    assert re.fullmatch(rf"1\.3\.0-dev\.1\.t[0-9]+\.g{sha}\n", result.stdout)


def test_preview_override_bypasses_git_and_is_not_shell_code(task_repo: Path) -> None:
    result = invoke(task_repo, "image:tag", "$(touch injected)")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "$(touch injected)\n"
    assert not (task_repo / "injected").exists()


@pytest.mark.parametrize("state", ["detached", "shallow"])
def test_incomplete_history_requires_an_override(task_repo: Path, state: str) -> None:
    initialize(task_repo)
    if state == "detached":
        git(task_repo, "checkout", "--detach")
    else:
        (task_repo / ".git/shallow").write_text(git(task_repo, "rev-parse", "HEAD") + "\n")
    result = invoke(task_repo, "publish")
    assert result.returncode != 0
    assert result.stdout == ""
    override = invoke(task_repo, "publish", "3.36.0-dev.manual")
    assert override.returncode == 0, override.stderr
    assert json.loads(override.stdout)["tag"] == "3.36.0-dev.manual"


def test_unrelated_tasks_do_not_calculate_an_image_version(task_repo: Path) -> None:
    result = invoke(task_repo, "registry:login")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['args'] == ['login', 'ghcr.io', '-u', 'example', '--password-stdin']
