from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from pytest_httpserver import HTTPServer

from warden.profiles.catalog import Document
from warden.profiles.files import write_catalog


pytestmark = pytest.mark.integration
APP_DIR = Path(__file__).resolve().parents[2]
REMOTE_PROFILE = {
    "id": 45, "name": "HD", "upgradeAllowed": True, "cutoff": 1000,
    "minFormatScore": 0, "cutoffFormatScore": 1000, "minUpgradeFormatScore": 1,
    "language": {"id": -2, "name": "Original"},
    "items": [
        {"id": 1, "quality": {"id": 1, "name": "SDTV"}, "allowed": False, "items": []},
        {"id": 1000, "name": "WEB 1080p", "allowed": True, "items": [
            {"quality": {"id": 3, "name": "WEBDL-1080p"}, "allowed": True, "items": []},
            {"quality": {"id": 15, "name": "WEBRip-1080p"}, "allowed": True, "items": []},
        ]},
    ],
    "formatItems": [{"format": 17, "name": "Preferred", "score": 100}],
}
REMOTE_FORMAT = {
    "id": 17, "name": "Preferred", "includeCustomFormatWhenRenaming": False,
    "specifications": [{
        "name": "Preferred release", "implementation": "ReleaseTitleSpecification",
        "negate": False, "required": True,
        "fields": [{"name": "value", "value": "Preferred", "label": "Regular Expression", "type": "textbox"}],
    }],
}


@pytest.fixture()
def output_directory() -> Iterator[Path]:
    # tmpfs is a verifiably local destination even when the workspace is an overlay.
    with TemporaryDirectory(prefix="warden-dump-test-", dir="/dev/shm") as directory:
        yield Path(directory) / "catalog"


def run_dump(server: HTTPServer, output: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "warden.profiles.cli", "dump", "--source", "radarr", "--output", str(output), *args],
        cwd=APP_DIR,
        env={**os.environ, "WARDEN_RADARR_URL": server.url_for(""), "WARDEN_RADARR_API_KEY": "secret-test-key",
             "WARDEN_DB_PATH": str(output.parent / "must-not-create.db"), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=15, check=False,
    )


def test_dump_reads_arr_and_produces_deterministic_portable_files(
    httpserver: HTTPServer, output_directory: Path,
) -> None:
    httpserver.expect_request("/api/v3/qualityprofile", method="GET", headers={"X-Api-Key": "secret-test-key"}).respond_with_json([REMOTE_PROFILE])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    first = run_dump(httpserver, output_directory)
    assert first.returncode == 0, first.stderr
    assert first.stdout == "Exported 1 profiles and 1 custom formats.\n"
    files = {str(p.relative_to(output_directory)): p.read_bytes() for p in output_directory.rglob("*") if p.is_file()}
    assert set(files) == {"radarr/profiles/HD.yml", "radarr/custom_formats/Preferred.json"}
    profile = files["radarr/profiles/HD.yml"].decode()
    assert "until_quality: WEB 1080p" in profile
    assert "language: Original" in profile
    assert "id:" not in profile
    assert "secret-test-key" not in profile
    assert json.loads(files["radarr/custom_formats/Preferred.json"])["specifications"][0]["fields"] == {"value": "Preferred"}
    mtimes = {p: p.stat().st_mtime_ns for p in output_directory.rglob("*") if p.is_file()}
    second = run_dump(httpserver, output_directory)
    assert second.returncode == 0, second.stderr
    assert {p: p.stat().st_mtime_ns for p in mtimes} == mtimes
    assert not (output_directory.parent / "must-not-create.db").exists()
    assert [(request.method, request.path) for request, _ in httpserver.log] == [
        ("GET", "/api/v3/qualityprofile"), ("GET", "/api/v3/customformat"),
        ("GET", "/api/v3/qualityprofile"), ("GET", "/api/v3/customformat"),
    ]
    validated = subprocess.run(
        [sys.executable, "-m", "warden.profiles.cli", "validate", "--directory", str(output_directory)],
        cwd=APP_DIR, capture_output=True, text=True, check=False, timeout=15,
    )
    assert validated.returncode == 0, validated.stderr


def test_failed_api_read_does_not_publish_output(httpserver: HTTPServer, output_directory: Path) -> None:
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_data("unavailable", status=503)
    result = run_dump(httpserver, output_directory)
    assert result.returncode == 1
    assert "503" in result.stderr
    assert not output_directory.exists()
    assert "secret-test-key" not in result.stderr


def test_collision_leaves_existing_files_untouched(httpserver: HTTPServer, output_directory: Path) -> None:
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    path = output_directory / "radarr/profiles/HD.yml"
    path.parent.mkdir(parents=True)
    path.write_text("user-authored content\n")
    result = run_dump(httpserver, output_directory)
    assert result.returncode == 1
    assert "collision" in result.stderr.lower()
    assert path.read_text() == "user-authored content\n"
    assert not (output_directory / "radarr/custom_formats").exists()


def test_unknown_profile_filter_does_not_publish_output(httpserver: HTTPServer, output_directory: Path) -> None:
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    result = run_dump(httpserver, output_directory, "--profile", "Missing")
    assert result.returncode == 1
    assert "unknown profile 'Missing'" in result.stderr
    assert not output_directory.exists()


def test_conflicting_name_in_another_file_blocks_export(httpserver: HTTPServer, output_directory: Path) -> None:
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    path = output_directory / "radarr/custom_formats/user-definition.json"
    path.parent.mkdir(parents=True)
    definition = {key: value for key, value in REMOTE_FORMAT.items() if key != "id"}
    definition["specifications"] = [{
        "name": "Different condition", "implementation": "ReleaseTitleSpecification",
        "negate": False, "required": True, "fields": {"value": "Different"},
    }]
    path.write_text(json.dumps(definition))
    before = path.read_bytes()
    result = run_dump(httpserver, output_directory)
    assert result.returncode == 1
    assert "duplicate custom format 'Preferred'" in result.stderr
    assert path.read_bytes() == before
    assert not (output_directory / "radarr/profiles").exists()


def test_writer_rejects_traversal_before_creating_files(output_directory: Path) -> None:
    document = Document("radarr", "profiles", "../escape.yml", {"schema_version": 1, "quality_profiles": []})
    with pytest.raises(ValueError, match="invalid catalog path"):
        write_catalog(output_directory, [document])
    assert not (output_directory.parent / "escape.yml").exists()
    assert not output_directory.exists()


def test_dump_and_diff_preserve_a_group_named_after_its_member(httpserver: HTTPServer, output_directory: Path) -> None:
    profile = deepcopy(REMOTE_PROFILE)
    profile["items"][1]["name"] = "WEBDL-1080p"
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([profile])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    dumped = run_dump(httpserver, output_directory)
    assert dumped.returncode == 0, dumped.stderr
    compared = subprocess.run(
        [sys.executable, "-m", "warden.profiles.cli", "diff", "--source", "radarr", "--directory", str(output_directory), "--json"],
        cwd=APP_DIR, env={**os.environ, "WARDEN_RADARR_URL": httpserver.url_for(""), "WARDEN_RADARR_API_KEY": "test-key"},
        capture_output=True, text=True, timeout=15,
    )
    assert compared.returncode == 0, compared.stderr
    assert json.loads(compared.stdout) == {"source": "radarr", "profiles": ["HD"], "changes": [], "conflicts": []}
    assert all(request.method == "GET" for request, _ in httpserver.log)
