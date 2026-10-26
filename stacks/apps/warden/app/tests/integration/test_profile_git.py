from __future__ import annotations

from pathlib import Path
import os

import pytest

from tests.integration.test_profile_observation import commit, git, repository
from warden.profiles.git import GitCatalog
from warden.profiles.settings import ProfileSettings


pytestmark = pytest.mark.integration


@pytest.fixture()
def subject(repository: Path) -> GitCatalog:
    config = ProfileSettings.from_env({
        "WARDEN_PROFILES_REPO": str(repository), "WARDEN_PROFILES_CACHE_DIR": str(repository.parent / "cache"),
        "WARDEN_PROFILES_TIMEOUT_SEC": "5",
    })
    return GitCatalog(config)


async def test_fetches_immutable_revision_and_unchanged_cycle_has_no_file_writes(subject: GitCatalog, repository: Path) -> None:
    snapshot = await subject.fetch()
    assert snapshot.commit == git(repository, "rev-parse", "HEAD")
    assert snapshot.documents[0].data["quality_profiles"][0]["custom_format_scores"] == {"Preferred": 100}
    cache = repository.parent / "cache"
    before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in cache.rglob("*") if p.is_file()}
    assert await subject.fetch() == snapshot
    assert {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in cache.rglob("*") if p.is_file()} == before


async def test_invalid_update_preserves_previous_snapshot(subject: GitCatalog, repository: Path) -> None:
    good = await subject.fetch()
    path = repository / "radarr/profiles/HD.yml"
    path.write_text("invalid: true\n")
    commit(repository, "broken catalog")
    with pytest.raises(ValueError):
        await subject.fetch()
    assert subject.current == good
    assert len(list((repository.parent / "cache").glob("snapshot-*"))) == 1


async def test_commit_pin_and_subdirectory(repository: Path) -> None:
    nested = repository / "catalog"
    nested.mkdir()
    (repository / "radarr").rename(nested / "radarr")
    pinned = commit(repository, "nested catalog")
    path = nested / "radarr/profiles/HD.yml"
    path.write_text(path.read_text().replace("Preferred: 100", "Preferred: 250"))
    commit(repository, "later revision")
    config = ProfileSettings.from_env({
        "WARDEN_PROFILES_REPO": str(repository), "WARDEN_PROFILES_REF": pinned,
        "WARDEN_PROFILES_PATH": "catalog", "WARDEN_PROFILES_CACHE_DIR": str(repository.parent / "cache"),
    })
    snapshot = await GitCatalog(config).fetch()
    assert snapshot.commit == pinned
    assert snapshot.documents[0].data["quality_profiles"][0]["custom_format_scores"] == {"Preferred": 100}


async def test_annotated_tag_resolves_commit(repository: Path) -> None:
    git(repository, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "tag", "-a", "v1", "-m", "catalog v1")
    config = ProfileSettings.from_env({
        "WARDEN_PROFILES_REPO": str(repository), "WARDEN_PROFILES_REF": "v1",
        "WARDEN_PROFILES_CACHE_DIR": str(repository.parent / "cache"),
    })
    assert (await GitCatalog(config).fetch()).commit == git(repository, "rev-parse", "HEAD")


async def test_budget_rejects_large_candidate_and_cleans_it(repository: Path) -> None:
    (repository / "large.bin").write_bytes(bytes(range(256)) * 4096)
    commit(repository, "oversized worktree")
    config = ProfileSettings.from_env({
        "WARDEN_PROFILES_REPO": str(repository), "WARDEN_PROFILES_CACHE_MAX_BYTES": "262144",
        "WARDEN_PROFILES_CACHE_DIR": str(repository.parent / "cache"),
    })
    with pytest.raises(ValueError, match="budget"):
        await GitCatalog(config).fetch()
    assert list((repository.parent / "cache").glob("snapshot-*")) == []


async def test_cache_cannot_adopt_existing_user_files(repository: Path) -> None:
    cache = repository.parent / "cache"
    cache.mkdir()
    user_file = cache / "keep.txt"
    user_file.write_text("user data")
    config = ProfileSettings.from_env({"WARDEN_PROFILES_REPO": str(repository), "WARDEN_PROFILES_CACHE_DIR": str(cache)})
    with pytest.raises(ValueError, match="dedicated"):
        await GitCatalog(config).fetch()
    assert user_file.read_text() == "user data"


async def test_cache_symlink_is_rejected(repository: Path) -> None:
    cache = repository.parent / "cache"
    cache.symlink_to(repository, target_is_directory=True)
    config = ProfileSettings.from_env({"WARDEN_PROFILES_REPO": str(repository), "WARDEN_PROFILES_CACHE_DIR": str(cache)})
    with pytest.raises(ValueError, match="symlink"):
        await GitCatalog(config).fetch()
    assert git(repository, "status", "--porcelain") == ""


async def test_restart_rebuilds_disposable_cache(subject: GitCatalog, repository: Path) -> None:
    before = await subject.fetch()
    restarted = GitCatalog(subject.settings)
    assert await restarted.fetch() == before
    assert len(list((repository.parent / "cache").glob("snapshot-*"))) == 1


async def test_timeout_kills_git_process(repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = tmp_path / "git"
    pidfile = tmp_path / "pid"
    executable.write_text('#!/usr/bin/env bash\nset -euo pipefail\necho "$$" > "$WARDEN_TEST_PIDFILE"\nexec sleep 30\n')
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setenv("WARDEN_TEST_PIDFILE", str(pidfile))
    config = ProfileSettings.from_env({
        "WARDEN_PROFILES_REPO": str(repository), "WARDEN_PROFILES_TIMEOUT_SEC": "0.2",
        "WARDEN_PROFILES_CACHE_DIR": str(repository.parent / "cache"),
    })
    with pytest.raises(TimeoutError):
        await GitCatalog(config).fetch()
    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text()), 0)
