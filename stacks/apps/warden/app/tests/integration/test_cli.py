from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.conftest import cli_env, invoke


pytestmark = pytest.mark.integration


@pytest.mark.parametrize("args", [(), ("--help",)])
def test_help_lists_commands_without_starting_the_server(tmp_path: Path, args: tuple[str, ...]) -> None:
    result = invoke(tmp_path, *args)
    assert result.returncode == 0, result.stderr
    assert "serve" in result.stdout and "profiles" in result.stdout
    assert result.stderr == ""
    assert not (tmp_path / "must-not-create.db").exists()


@pytest.mark.parametrize("args", [("unknown",), ("serve", "--unknown"), ("profiles",), ("profiles", "dump")])
def test_invalid_commands_report_usage_without_starting_the_server(tmp_path: Path, args: tuple[str, ...]) -> None:
    result = invoke(tmp_path, *args)
    assert result.returncode == 2
    assert "usage: warden" in result.stderr
    assert result.stdout == ""
    assert not (tmp_path / "must-not-create.db").exists()


@pytest.mark.parametrize("setting,field", [
    ("WARDEN_METRICS_PORT", "metrics_port"),
    ("WARDEN_INCLUDE_CUTOFF_UNMET", "include_cutoff_unmet"),
    ("WARDEN_MIN_FREE_GB", "min_free_gb"),
])
def test_invalid_server_setting_identifies_field_without_exposing_input(tmp_path: Path, setting: str, field: str) -> None:
    env = cli_env(tmp_path)
    env.update(WARDEN_METRICS_PORT="9090", WARDEN_RADARR_API_KEY="private-api-key")
    env[setting] = "private-invalid-value"
    result = invoke(tmp_path, "serve", env=env)
    assert result.returncode == 1
    assert field in result.stderr.lower()
    assert "private-invalid-value" not in result.stderr
    assert "private-api-key" not in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "must-not-create.db").exists()
