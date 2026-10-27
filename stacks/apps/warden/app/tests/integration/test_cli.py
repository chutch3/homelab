from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.conftest import invoke


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
