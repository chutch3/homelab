from __future__ import annotations

from pathlib import Path

import pytest

from warden.profiles.settings import ProfileSettings, parse_selection


def test_repository_unset_disables_profiles_without_parsing_other_values() -> None:
    assert ProfileSettings.from_env({"WARDEN_PROFILES_INTERVAL_SEC": "bad"}) is None


def test_defaults_are_observation_with_bounded_local_cache() -> None:
    config = ProfileSettings.from_env({"WARDEN_PROFILES_REPO": "https://example.invalid/profiles.git"})
    assert config.repo == "https://example.invalid/profiles.git"
    assert (config.ref, config.path, config.interval, config.timeout) == ("main", ".", 900.0, 60.0)
    assert config.cache == Path("/profile-cache")
    assert config.max_bytes == 32 * 1024 * 1024


@pytest.mark.parametrize("setting,value", [
    ("MODE", "sync"), ("INTERVAL_SEC", "0"), ("INTERVAL_SEC", "nan"), ("TIMEOUT_SEC", "inf"),
    ("CACHE_MAX_BYTES", "0"), ("PATH", "../outside"), ("PATH", "/outside"), ("REF", "--upload-pack=bad"),
    ("REPO", "https://user:secret@example.invalid/profiles.git"),
])
def test_invalid_settings_are_rejected(setting: str, value: str) -> None:
    env = {"WARDEN_PROFILES_REPO": "https://example.invalid/profiles.git", f"WARDEN_PROFILES_{setting}": value}
    with pytest.raises(ValueError) as error:
        ProfileSettings.from_env(env)
    assert "secret" not in str(error.value)


def test_selection_defaults_and_exact_names() -> None:
    assert parse_selection(None) is None
    assert parse_selection("[]") == []
    assert parse_selection('["HD", "Movies"]') == ["HD", "Movies"]


@pytest.mark.parametrize("value", ["", "null", "{}", "[1]", '[""]'])
def test_selection_rejects_malformed_or_empty_names(value: str) -> None:
    with pytest.raises(ValueError):
        parse_selection(value)


@pytest.mark.parametrize("repo", ["ssh://user:secret@example.invalid/profiles.git", "https://example.invalid/profiles.git?token=secret"])
def test_repository_credentials_must_stay_out_of_urls(repo: str) -> None:
    with pytest.raises(ValueError) as error:
        ProfileSettings.from_env({"WARDEN_PROFILES_REPO": repo})
    assert "secret" not in str(error.value)


def test_directory_source_is_enabled_without_a_repository() -> None:
    config = ProfileSettings.from_env({"WARDEN_PROFILES_DIRECTORY": "/profiles"})
    assert config.directory == Path("/profiles")
    assert config.repo == ""
    assert config.interval == 900


@pytest.mark.parametrize("directory", ["relative", "/profiles/../other"])
def test_directory_must_be_an_absolute_unambiguous_path(directory: str) -> None:
    with pytest.raises(ValueError, match="directory"):
        ProfileSettings.from_env({"WARDEN_PROFILES_DIRECTORY": directory})


def test_repository_and_directory_are_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        ProfileSettings.from_env({"WARDEN_PROFILES_REPO": "https://example.invalid/profiles.git", "WARDEN_PROFILES_DIRECTORY": "/profiles"})


def test_explicit_profile_environment_does_not_inherit_process_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WARDEN_PROFILES_DIRECTORY", "/unwanted")
    monkeypatch.setenv("WARDEN_PROFILES_TIMEOUT_SEC", "invalid")
    config = ProfileSettings.from_env({"WARDEN_PROFILES_REPO": "https://example.invalid/profiles.git"})
    assert config.directory is None
    assert config.timeout == 60


def test_empty_profile_directory_is_unset() -> None:
    config = ProfileSettings.from_env({"WARDEN_PROFILES_REPO": "https://example.invalid/profiles.git", "WARDEN_PROFILES_DIRECTORY": ""})
    assert config.directory is None
