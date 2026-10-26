from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from pytest_httpserver import HTTPServer

from tests.integration.test_profile_dump import (
    APP_DIR, REMOTE_FORMAT, REMOTE_PROFILE, output_directory, run_dump,
)
from warden.profiles.cli import main


pytestmark = pytest.mark.integration


def run_diff(server: HTTPServer, directory: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("WARDEN_")}
    env.update(WARDEN_RADARR_URL=server.url_for(""), WARDEN_RADARR_API_KEY="test-key",
               PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, "-m", "warden.profiles.cli", "diff", "--source", "radarr",
         "--directory", str(directory), *args],
        cwd=APP_DIR, env=env, capture_output=True, text=True, timeout=15, check=False,
    )


@pytest.fixture()
def dumped_catalog(httpserver: HTTPServer, output_directory: Path) -> Path:
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    result = run_dump(httpserver, output_directory)
    assert result.returncode == 0, result.stderr
    httpserver.clear_log()
    return output_directory


def test_dump_then_diff_is_clean_and_read_only(httpserver: HTTPServer, dumped_catalog: Path) -> None:
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in dumped_catalog.rglob("*") if p.is_file()}
    result = run_diff(httpserver, dumped_catalog, "--json")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"source": "radarr", "profiles": ["HD"], "changes": [], "conflicts": []}
    assert result.stderr == ""
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before} == before
    assert [(r.method, r.path) for r, _ in httpserver.log] == [
        ("GET", "/api/v3/qualityprofile"), ("GET", "/api/v3/customformat"),
    ]


def test_changed_score_has_one_precise_difference(httpserver: HTTPServer, dumped_catalog: Path) -> None:
    path = dumped_catalog / "radarr/profiles/HD.yml"
    path.write_text(path.read_text().replace("Preferred: 100", "Preferred: 250"))
    result = run_diff(httpserver, dumped_catalog, "--json")
    assert result.returncode == 2, result.stderr
    assert json.loads(result.stdout) == {
        "source": "radarr", "profiles": ["HD"], "conflicts": [],
        "changes": [{"kind": "profile", "name": "HD", "field": "custom_format_scores.Preferred", "current": 100, "desired": 250}],
    }
    human = run_diff(httpserver, dumped_catalog)
    assert human.returncode == 2
    assert human.stdout == 'radarr: 1 change across 1 resource.\n  profile "HD": custom_format_scores.Preferred: 100 -> 250\n'
    assert all(r.method == "GET" for r, _ in httpserver.log)


def test_shared_format_change_reports_unselected_profiles(httpserver: HTTPServer, dumped_catalog: Path) -> None:
    path = dumped_catalog / "radarr/custom_formats/Preferred.json"
    data = json.loads(path.read_text())
    data["specifications"][0]["fields"]["value"] = "New pattern"
    path.write_text(json.dumps(data))
    httpserver.clear_all_handlers()
    other = {**deepcopy(REMOTE_PROFILE), "id": 46, "name": "Other"}
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE, other])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    result = run_diff(httpserver, dumped_catalog, "--json")
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["conflicts"] == [{"kind": "custom_format", "name": "Preferred", "profiles": ["Other"]}]
    assert report["changes"] == [{
        "kind": "custom_format", "name": "Preferred", "field": "specifications.Preferred release.fields.value",
        "current": "Preferred", "desired": "New pattern",
    }]


def test_unknown_selection_fails_before_api_requests(httpserver: HTTPServer, dumped_catalog: Path) -> None:
    result = run_diff(httpserver, dumped_catalog, "--profile", "Missing", "--json")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "unknown profile 'Missing'" in result.stderr
    assert httpserver.log == []


def test_failed_read_is_not_reported_as_clean(httpserver: HTTPServer, dumped_catalog: Path) -> None:
    httpserver.clear_all_handlers()
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_data("unavailable", status=503)
    result = run_diff(httpserver, dumped_catalog, "--json")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "503" in result.stderr
    assert "test-key" not in result.stderr


def test_new_profile_is_reported_as_missing(httpserver: HTTPServer, dumped_catalog: Path) -> None:
    httpserver.clear_all_handlers()
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([])
    result = run_diff(httpserver, dumped_catalog, "--json")
    assert result.returncode == 2, result.stderr
    report = json.loads(result.stdout)
    assert [(c["kind"], c["name"], c["field"], c["current"]) for c in report["changes"]] == [
        ("custom_format", "Preferred", "$", None), ("profile", "HD", "$", None),
    ]
    assert report["changes"][1]["desired"]["name"] == "HD"


def test_existing_cli_entry_uses_environment_filter(
    httpserver: HTTPServer, dumped_catalog: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("WARDEN_RADARR_URL", httpserver.url_for(""))
    monkeypatch.setenv("WARDEN_RADARR_API_KEY", "test-key")
    monkeypatch.setenv("WARDEN_RADARR_PROFILES", "[]")
    assert main(["diff", "--source", "radarr", "--directory", str(dumped_catalog), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"source": "radarr", "profiles": [], "changes": [], "conflicts": []}
    assert httpserver.log == []
    assert main(["diff", "--source", "radarr", "--directory", str(dumped_catalog), "--profile", "HD"]) == 0
    assert capsys.readouterr().out == "radarr: no differences (1 profile).\n"


def test_invalid_remote_score_is_an_error(httpserver: HTTPServer, dumped_catalog: Path) -> None:
    profile = deepcopy(REMOTE_PROFILE)
    profile["formatItems"][0]["score"] = True
    httpserver.clear_all_handlers()
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([profile])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    result = run_diff(httpserver, dumped_catalog, "--json")
    assert result.returncode == 1
    assert "score" in result.stderr.lower()
    assert result.stdout == ""


@pytest.mark.parametrize("case", ["quality_flag", "upgrade_flag", "threshold", "rename_flag", "condition_flag"])
def test_invalid_remote_types_cannot_look_clean(httpserver: HTTPServer, dumped_catalog: Path, case: str) -> None:
    profile, custom_format = deepcopy(REMOTE_PROFILE), deepcopy(REMOTE_FORMAT)
    if case == "quality_flag":
        profile["items"][1]["allowed"] = 1
        for child in profile["items"][1]["items"]:
            child["allowed"] = 1
    elif case == "upgrade_flag":
        profile["upgradeAllowed"] = 1
    elif case == "threshold":
        profile["minUpgradeFormatScore"] = True
    elif case == "rename_flag":
        custom_format["includeCustomFormatWhenRenaming"] = 0
    else:
        custom_format["specifications"][0]["negate"] = 0
    httpserver.clear_all_handlers()
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([profile])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([custom_format])
    result = run_diff(httpserver, dumped_catalog, "--json")
    assert result.returncode == 1
    assert "invalid" in result.stderr.lower()
    assert result.stdout == ""


@pytest.mark.parametrize("selection", ["", "null", "{}", '[1]', '["Unknown"]'])
def test_invalid_environment_selection_is_an_error_before_network(
    httpserver: HTTPServer, dumped_catalog: Path, selection: str,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("WARDEN_RADARR_PROFILES", selection)
    assert main(["diff", "--source", "radarr", "--directory", str(dumped_catalog), "--json"]) == 1
    result = capsys.readouterr()
    assert result.out == ""
    assert result.err.startswith("error:")
    assert httpserver.log == []


def test_invalid_local_catalog_prevents_reads(httpserver: HTTPServer, dumped_catalog: Path) -> None:
    path = dumped_catalog / "radarr/profiles/HD.yml"
    path.write_text(path.read_text().replace("until_score:", "untill_score:"))
    result = run_diff(httpserver, dumped_catalog, "--json")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "untill_score" in result.stderr
    assert httpserver.log == []
