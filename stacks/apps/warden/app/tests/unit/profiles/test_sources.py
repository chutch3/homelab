from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from warden.clients.git import GitClient
from warden.profiles.cache import SnapshotCache
from warden.profiles.files import ProfileStore
from warden.profiles.models import ProfileDocument, ProfileSnapshot
from warden.profiles.sources import DirectoryProfileSource, GitProfileSource


class TestDirectoryProfileSource:
    @pytest.fixture()
    def subject(self) -> DirectoryProfileSource:
        store = Mock(spec=ProfileStore)
        store.load.return_value = (ProfileDocument("radarr", "profiles", "hd.yml", {"name": "HD"}),)
        return DirectoryProfileSource(Path("/profiles"), store, max_bytes=7)

    async def test_fetch_reads_with_byte_limit_and_returns_stable_revision(self, subject: DirectoryProfileSource) -> None:
        first = await subject.fetch()
        second = await subject.fetch()
        assert first == second
        assert first.documents == subject.store.load.return_value
        assert first.commit.startswith("directory:")
        assert len(first.commit) == len("directory:") + 64
        subject.store.load.assert_has_calls([call(Path("/profiles"), 7), call(Path("/profiles"), 7)])
        subject.store.write.assert_not_called()

    async def test_fetch_changed_document_changes_revision(self, subject: DirectoryProfileSource) -> None:
        first = await subject.fetch()
        subject.store.load.return_value = (ProfileDocument("radarr", "profiles", "hd.yml", {"name": "UHD"}),)
        second = await subject.fetch()
        assert second.commit != first.commit
        assert second.documents == subject.store.load.return_value

    async def test_fetch_read_failure_propagates(self, subject: DirectoryProfileSource) -> None:
        subject.store.load.side_effect = ValueError("invalid profiles")
        with pytest.raises(ValueError, match="invalid profiles"):
            await subject.fetch()


class TestGitProfileSource:
    @pytest.fixture()
    def subject(self) -> GitProfileSource:
        git = Mock(spec=GitClient)
        git.resolve.return_value = "a" * 40
        cache = Mock(spec=SnapshotCache)
        cache.create.return_value = Path("/cache/snapshot-new")
        cache.profile_directory.return_value = Path("/cache/snapshot-new/profiles")
        store = Mock(spec=ProfileStore)
        store.load.return_value = (ProfileDocument("radarr", "profiles", "hd.yml", {}),)
        return GitProfileSource("https://example.invalid/profiles", "main", "profiles", git, cache, store)

    async def test_fetch_adopts_validated_checkout(self, subject: GitProfileSource) -> None:
        result = await subject.fetch()
        assert result == ProfileSnapshot("a" * 40, subject.store.load.return_value)
        assert subject.current == result
        subject.git.resolve.assert_awaited_once_with(subject.repo, "main")
        subject.git.checkout.assert_awaited_once_with(subject.repo, "a" * 40, Path("/cache/snapshot-new"))
        subject.cache.prepare.assert_called_once_with(None)
        subject.cache.profile_directory.assert_called_once_with(Path("/cache/snapshot-new"), "profiles")
        subject.store.load.assert_called_once_with(Path("/cache/snapshot-new/profiles"))
        subject.cache.discard.assert_not_called()

    async def test_fetch_unchanged_revision_reuses_present_snapshot(self, subject: GitProfileSource) -> None:
        first = await subject.fetch()
        subject.cache.contains.return_value = True
        assert await subject.fetch() is first
        assert subject.git.checkout.await_count == 1
        assert subject.store.load.call_count == 1
        subject.cache.contains.assert_called_once_with(Path("/cache/snapshot-new"))

    async def test_fetch_missing_checkout_is_fetched_again(self, subject: GitProfileSource) -> None:
        await subject.fetch()
        subject.cache.contains.return_value = False
        subject.cache.create.return_value = Path("/cache/snapshot-replacement")
        await subject.fetch()
        assert subject.git.checkout.await_count == 2
        subject.cache.discard.assert_called_once_with(Path("/cache/snapshot-new"))

    async def test_fetch_replaces_old_snapshot_only_after_validation(self, subject: GitProfileSource) -> None:
        await subject.fetch()
        subject.git.resolve.return_value = "b" * 40
        subject.cache.create.return_value = Path("/cache/snapshot-next")
        def validate(directory: Path) -> tuple[ProfileDocument, ...]:
            subject.cache.discard.assert_not_called()
            assert subject.current.commit == "a" * 40
            return ()
        subject.store.load.side_effect = validate
        assert await subject.fetch() == ProfileSnapshot("b" * 40, ())
        subject.cache.discard.assert_called_once_with(Path("/cache/snapshot-new"))

    @pytest.mark.parametrize("failure", ["checkout", "load", "budget", "path"])
    async def test_fetch_failed_candidate_keeps_previous_snapshot(self, subject: GitProfileSource, failure: str) -> None:
        previous = await subject.fetch()
        subject.git.resolve.return_value = "b" * 40
        subject.cache.create.return_value = Path("/cache/snapshot-next")
        targets = {"checkout": subject.git.checkout, "load": subject.store.load,
                   "budget": subject.cache.check, "path": subject.cache.profile_directory}
        if failure == "budget":
            subject.cache.check.side_effect = [None, ValueError("failed candidate")]
        else:
            targets[failure].side_effect = ValueError("failed candidate")
        with pytest.raises(ValueError, match="failed candidate"):
            await subject.fetch()
        assert subject.current is previous
        subject.cache.discard.assert_called_once_with(Path("/cache/snapshot-next"))

    async def test_fetch_cancelled_checkout_discards_candidate(self, subject: GitProfileSource) -> None:
        subject.git.checkout.side_effect = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await subject.fetch()
        assert subject.current is None
        subject.cache.discard.assert_called_once_with(Path("/cache/snapshot-new"))

    async def test_fetch_resolution_failure_never_creates_candidate(self, subject: GitProfileSource) -> None:
        subject.git.resolve.side_effect = ValueError("missing ref")
        with pytest.raises(ValueError, match="missing ref"):
            await subject.fetch()
        subject.cache.create.assert_not_called()
        subject.store.load.assert_not_called()
