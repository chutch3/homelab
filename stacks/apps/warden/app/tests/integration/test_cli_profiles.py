from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pytest_httpserver import HTTPServer

from tests.profile_data import REMOTE_FORMAT, REMOTE_PROFILE, PROFILE
from tests.integration.conftest import cli_env, invoke, run_diff, run_dump, run_validate, EXAMPLES


pytestmark = pytest.mark.integration


def test_dump_keeps_resource_names_inside_output_directory(httpserver: HTTPServer, output_directory: Path) -> None:
    profile = {**deepcopy(REMOTE_PROFILE), "name": "../escape"}
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([profile])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    result = run_dump(httpserver, output_directory)
    assert result.returncode == 0, result.stderr
    assert {str(path.relative_to(output_directory)) for path in output_directory.rglob("*") if path.is_file()} == {
        "radarr/profiles/..%2Fescape.yml", "radarr/custom_formats/Preferred.json",
    }
    assert not (output_directory / "radarr/escape.yml").exists()
    assert not (output_directory.parent / "escape.yml").exists()
    assert run_validate(output_directory).returncode == 0


def test_dump_rejects_symlinked_output_without_writing(httpserver: HTTPServer, output_directory: Path) -> None:
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    actual = output_directory.parent / "actual"
    actual.mkdir()
    output_directory.symlink_to(actual, target_is_directory=True)
    result = run_dump(httpserver, output_directory)
    assert result.returncode == 1
    assert "symlink" in result.stderr
    assert list(actual.iterdir()) == []


def test_validates_portable_catalog_without_writing_files(catalog: Path) -> None:
    before = {str(p.relative_to(catalog)): p.read_bytes() for p in catalog.rglob("*") if p.is_file()}
    result = run_validate(catalog)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Valid catalog: 2 profiles, 2 custom formats.\n"
    assert result.stderr == ""
    after = {str(p.relative_to(catalog)): p.read_bytes() for p in catalog.rglob("*") if p.is_file()}
    assert after == before


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
    validated = run_validate(output_directory)
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


def test_dump_and_diff_preserve_a_group_named_after_its_member(httpserver: HTTPServer, output_directory: Path) -> None:
    profile = deepcopy(REMOTE_PROFILE)
    profile["items"][1]["name"] = "WEBDL-1080p"
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([profile])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    dumped = run_dump(httpserver, output_directory)
    assert dumped.returncode == 0, dumped.stderr
    compared = run_diff(httpserver, output_directory, "--json")
    assert compared.returncode == 0, compared.stderr
    assert json.loads(compared.stdout) == {"source": "radarr", "profiles": ["HD"], "changes": [], "conflicts": []}
    assert all(request.method == "GET" for request, _ in httpserver.log)


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


def test_cli_uses_environment_filter(httpserver: HTTPServer, dumped_catalog: Path) -> None:
    env = {"WARDEN_RADARR_PROFILES": "[]"}
    result = run_diff(httpserver, dumped_catalog, "--json", env=env)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"source": "radarr", "profiles": [], "changes": [], "conflicts": []}
    assert httpserver.log == []
    result = run_diff(httpserver, dumped_catalog, "--profile", "HD", env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "radarr: no differences (1 profile).\n"


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
) -> None:
    result = run_diff(httpserver, dumped_catalog, "--json", env={"WARDEN_RADARR_PROFILES": selection})
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("error:")
    assert httpserver.log == []


def test_invalid_local_catalog_prevents_reads(httpserver: HTTPServer, dumped_catalog: Path) -> None:
    path = dumped_catalog / "radarr/profiles/HD.yml"
    path.write_text(path.read_text().replace("until_score:", "untill_score:"))
    result = run_diff(httpserver, dumped_catalog, "--json")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "untill_score" in result.stderr
    assert httpserver.log == []


def test_profiles_validate_without_server_configuration(tmp_path: Path) -> None:
    result = invoke(tmp_path, "profiles", "validate", "--directory", str(EXAMPLES))
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Valid catalog: 1 profiles, 1 custom formats.\n"
    assert not (tmp_path / "must-not-create.db").exists()


def test_profiles_validation_error_retains_exit_status(tmp_path: Path) -> None:
    result = invoke(tmp_path, "profiles", "validate", "--directory", str(tmp_path / "missing"))
    assert result.returncode == 1
    assert "catalog directory does not exist" in result.stderr
    assert result.stdout == ""
    assert not (tmp_path / "must-not-create.db").exists()


def test_profiles_dump_and_diff_remain_read_only(httpserver: HTTPServer, output_directory: Path) -> None:
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    work = output_directory.parent
    env = cli_env(work)
    env.update(WARDEN_RADARR_URL=httpserver.url_for(""), WARDEN_RADARR_API_KEY="test-key")
    dumped = invoke(work, "profiles", "dump", "--source", "radarr", "--output", str(output_directory), env=env)
    assert dumped.returncode == 0, dumped.stderr
    assert dumped.stdout == "Exported 1 profiles and 1 custom formats.\n"
    args = ("profiles", "diff", "--source", "radarr", "--directory", str(output_directory), "--json")
    clean = invoke(work, *args, env=env)
    assert clean.returncode == 0, clean.stderr
    assert json.loads(clean.stdout) == {"source": "radarr", "profiles": ["HD"], "changes": [], "conflicts": []}
    path = output_directory / "radarr/profiles/HD.yml"
    profile = yaml.safe_load(path.read_text())
    profile["quality_profiles"][0]["custom_format_scores"]["Preferred"] = 250
    path.write_text(yaml.safe_dump(profile))
    drift = invoke(work, *args, env=env)
    assert drift.returncode == 2, drift.stderr
    assert json.loads(drift.stdout)["changes"] == [
        {"kind": "profile", "name": "HD", "field": "custom_format_scores.Preferred", "current": 100, "desired": 250},
    ]
    assert [(request.method, request.path) for request, _ in httpserver.log] == [
        ("GET", "/api/v3/qualityprofile"), ("GET", "/api/v3/customformat"),
    ] * 3
    assert not (work / "must-not-create.db").exists()
