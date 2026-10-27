from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.e2e
APP_DIR = Path(__file__).resolve().parents[2]


def test_installed_cli_and_wheel_work_outside_the_checkout(tmp_path: Path) -> None:
    installed = Path(sys.executable).with_name("warden")
    assert installed.is_file(), "project installation must provide the warden executable"
    project = tmp_path / "source"
    project.mkdir()
    shutil.copyfile(APP_DIR / "pyproject.toml", project / "pyproject.toml")
    shutil.copytree(APP_DIR / "warden", project / "warden", ignore=shutil.ignore_patterns("__pycache__"))
    built = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path / "dist")], cwd=project,
        capture_output=True, text=True, timeout=60,
    )
    assert built.returncode == 0, built.stderr
    wheels = list((tmp_path / "dist").glob("*.whl"))
    assert len(wheels) == 1
    target = tmp_path / "installed"
    result = subprocess.run(
        ["uv", "pip", "install", "--python", sys.executable, "--no-deps", "--target", str(target), str(wheels[0])],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    shutil.rmtree(project)
    env = {key: value for key, value in os.environ.items() if not key.startswith("WARDEN_")}
    env.update(PYTHONPATH=str(target), PYTHONDONTWRITEBYTECODE="1", WARDEN_METRICS_PORT="invalid",
               WARDEN_DB_URL=f"sqlite:///{tmp_path}/must-not-create.db")
    located = subprocess.run(
        [sys.executable, "-c", "import warden; print(warden.__file__)"], cwd=tmp_path,
        env=env, capture_output=True, text=True, timeout=15,
    )
    assert located.returncode == 0, located.stderr
    assert Path(located.stdout.strip()).is_relative_to(target)
    for command in ([str(target / "bin/warden")], [sys.executable, "-m", "warden"]):
        validated = subprocess.run(
            [*command, "profiles", "validate", "--directory", str(APP_DIR.parent / "examples/profiles")],
            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15,
        )
        assert validated.returncode == 0, validated.stderr
        assert validated.stdout == "Valid catalog: 1 profiles, 1 custom formats.\n"
    assert not (tmp_path / "must-not-create.db").exists()
