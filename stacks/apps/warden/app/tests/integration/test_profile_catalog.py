from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from warden.profiles.catalog_io import DirectoryCatalog, load_catalog


pytestmark = pytest.mark.integration
APP_DIR = Path(__file__).resolve().parents[2]
PROFILE = """schema_version: 1
quality_profiles:
  - name: HD
    upgrade:
      allowed: true
      until_quality: WEB 1080p
      until_score: 1000
    min_format_score: 0
    min_upgrade_format_score: 1
    qualities:
      - name: WEB 1080p
        qualities: [WEBDL-1080p, WEBRip-1080p]
    custom_format_scores:
      Preferred: 100
"""
CUSTOM_FORMAT = {
    "name": "Preferred",
    "includeCustomFormatWhenRenaming": False,
    "specifications": [{
        "name": "Preferred release", "implementation": "ReleaseTitleSpecification",
        "negate": False, "required": True,
        "fields": [{"name": "value", "value": "\\bPreferred\\b"}],
    }],
}


@pytest.fixture()
def catalog(tmp_path: Path) -> Path:
    root = tmp_path / "catalog"
    for source in ("radarr", "sonarr"):
        profiles = root / source / "profiles"
        formats = root / source / "custom_formats"
        profiles.mkdir(parents=True)
        formats.mkdir()
        (profiles / "hd.yml").write_text(PROFILE)
        (formats / "preferred.json").write_text(json.dumps(CUSTOM_FORMAT))
    return root


def run_validate(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "warden.profiles.cli", "validate", "--directory", str(root)],
        cwd=APP_DIR, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=15, check=False,
    )


def test_validates_portable_catalog_without_writing_files(catalog: Path) -> None:
    before = {str(p.relative_to(catalog)): p.read_bytes() for p in catalog.rglob("*") if p.is_file()}
    result = run_validate(catalog)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Valid catalog: 2 profiles, 2 custom formats.\n"
    assert result.stderr == ""
    after = {str(p.relative_to(catalog)): p.read_bytes() for p in catalog.rglob("*") if p.is_file()}
    assert after == before


async def test_directory_snapshot_is_read_only_and_content_addressed(catalog: Path) -> None:
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in catalog.rglob('*') if p.is_file()}
    reader = DirectoryCatalog(catalog)
    first = await reader.fetch()
    assert first.commit.startswith('directory:')
    assert len(first.documents) == 4
    assert await reader.fetch() == first
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in catalog.rglob('*') if p.is_file()} == before
    path = catalog / 'radarr/profiles/hd.yml'
    path.write_text(path.read_text().replace('Preferred: 100', 'Preferred: 250'))
    assert (await reader.fetch()).commit != first.commit


async def test_directory_reader_enforces_byte_limit(catalog: Path) -> None:
    with pytest.raises(ValueError, match='budget'):
        await DirectoryCatalog(catalog, max_bytes=20).fetch()


async def test_directory_reader_rejects_symlinked_parent(catalog: Path) -> None:
    link = catalog.parent / 'alias'
    link.symlink_to(catalog.parent, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        await DirectoryCatalog(link / catalog.name).fetch()


def test_reports_unknown_fields_with_filename_and_field_path(catalog: Path) -> None:
    path = catalog / "radarr/profiles/hd.yml"
    path.write_text(PROFILE.replace("until_score", "untill_score"))
    result = run_validate(catalog)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "radarr/profiles/hd.yml" in result.stderr
    assert "quality_profiles[0].upgrade" in result.stderr
    assert "untill_score" in result.stderr


def test_missing_dependency_is_not_satisfied_by_other_application(catalog: Path) -> None:
    (catalog / "radarr/custom_formats/preferred.json").unlink()
    result = run_validate(catalog)
    assert result.returncode == 1
    assert "radarr/profiles/hd.yml" in result.stderr
    assert "unknown custom format 'Preferred'" in result.stderr


def test_rejects_empty_catalog(tmp_path: Path) -> None:
    result = run_validate(tmp_path)
    assert result.returncode == 1
    assert "no profiles" in result.stderr.lower()


def test_rejects_unknown_schema_version(catalog: Path) -> None:
    (catalog / "radarr/profiles/hd.yml").write_text(PROFILE.replace("schema_version: 1", "schema_version: 2"))
    result = run_validate(catalog)
    assert result.returncode == 1
    assert "schema_version" in result.stderr


def test_rejects_duplicate_yaml_keys(catalog: Path) -> None:
    (catalog / "radarr/profiles/hd.yml").write_text(PROFILE.replace("Preferred: 100", "Preferred: 100\n      Preferred: 200"))
    result = run_validate(catalog)
    assert result.returncode == 1
    assert "duplicate key" in result.stderr.lower()


def test_rejects_symlinked_catalog_files(catalog: Path, tmp_path: Path) -> None:
    target = tmp_path / "outside.yml"
    target.write_text(PROFILE)
    path = catalog / "radarr/profiles/hd.yml"
    path.unlink()
    path.symlink_to(target)
    result = run_validate(catalog)
    assert result.returncode == 1
    assert "symlink" in result.stderr.lower()


def test_rejects_unsafe_yaml_tags(catalog: Path) -> None:
    (catalog / "radarr/profiles/hd.yml").write_text("!!python/object:os.system {}")
    result = run_validate(catalog)
    assert result.returncode == 1
    assert "radarr/profiles/hd.yml" in result.stderr
    assert "Traceback" not in result.stderr


def test_accepts_community_export_fields_and_preserves_metadata(catalog: Path) -> None:
    path = catalog / "radarr/custom_formats/preferred.json"
    data = json.loads(path.read_text())
    data["trash_id"] = "820b09bb9acbfde9c35c71e0e565dad8"
    data["trash_scores"] = {"default": 50}
    data["specifications"][0]["fields"] = {"value": "\\bPreferred\\b"}
    path.write_text(json.dumps(data))
    result = run_validate(catalog)
    assert result.returncode == 0, result.stderr
    assert json.loads(path.read_text()) == data


@pytest.mark.parametrize("value", [True, 1.5, "100", 2147483648, -2147483649])
def test_rejects_invalid_score_types_and_bounds(catalog: Path, value: object) -> None:
    path = catalog / "radarr/profiles/hd.yml"
    path.write_text(PROFILE.replace("Preferred: 100", f"Preferred: {json.dumps(value)}"))
    result = run_validate(catalog)
    assert result.returncode == 1
    assert "custom_format_scores.Preferred" in result.stderr


def test_load_catalog_exposes_validated_documents(catalog: Path) -> None:
    documents = load_catalog(catalog)
    assert [(d.source, d.kind, d.path) for d in documents] == [
        ("radarr", "profiles", "radarr/profiles/hd.yml"),
        ("radarr", "custom_formats", "radarr/custom_formats/preferred.json"),
        ("sonarr", "profiles", "sonarr/profiles/hd.yml"),
        ("sonarr", "custom_formats", "sonarr/custom_formats/preferred.json"),
    ]
    assert documents[0].data["quality_profiles"][0]["custom_format_scores"] == {"Preferred": 100}
