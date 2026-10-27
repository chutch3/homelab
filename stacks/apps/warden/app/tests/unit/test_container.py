from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest

from warden.arr_service import ArrService
from warden.clients.arr import RadarrClient, SonarrClient
from warden.clients.git import GitClient
from warden.clock import SystemClock
from warden.container import Container
from warden.metrics import Metrics
from warden.profiles.cache import SnapshotCache
from warden.profiles.files import ProfileStore
from warden.profiles.observer import Observer
from warden.profiles.reading import DocumentCodec, ProfileFiles
from warden.profiles.sources import DirectoryProfileSource, GitProfileSource, ProfileSource


class TestContainer:
    @pytest.fixture()
    def subject(self) -> Iterator[Container]:
        container = Container()
        container.environment.override({
            "WARDEN_RADARR_URL": "http://radarr.invalid", "WARDEN_RADARR_API_KEY": "test-key",
            "WARDEN_SONARR_URL": "http://sonarr.invalid", "WARDEN_SONARR_API_KEY": "test-key",
            "WARDEN_METRICS_PORT": "invalid", "WARDEN_PROFILES_DIRECTORY": "/profiles",
        })
        container.radarr_client.override(Mock(spec=RadarrClient))
        container.sonarr_client.override(Mock(spec=SonarrClient))
        container.profile_files.override(Mock(spec=ProfileFiles))
        container.profile_codec.override(Mock(spec=DocumentCodec))
        container.metrics.override(Mock(spec=Metrics))
        container.clock.override(Mock(spec=SystemClock))
        try:
            yield container
        finally:
            container.unwire()

    def test_profile_store_receives_registered_dependencies_without_http(self, subject: Container) -> None:
        store = subject.profile_store()
        assert isinstance(store, ProfileStore)
        assert store.files is subject.profile_files()
        assert store.codec is subject.profile_codec()
        assert subject.profile_store() is store
        assert not subject.http.initialized

    def test_arr_service_shares_registered_clients_with_hunter(self, subject: Container) -> None:
        arr = subject.arr_service()
        assert isinstance(arr, ArrService)
        assert arr.clients == {"radarr": subject.radarr_client(), "sonarr": subject.sonarr_client()}
        assert subject.clients() == list(arr.clients.values())
        assert subject.arr_service() is arr
        assert not subject.http.initialized

    def test_arr_service_excludes_unconfigured_instance(self, subject: Container) -> None:
        subject.environment.override({"WARDEN_RADARR_URL": "http://radarr.invalid", "WARDEN_RADARR_API_KEY": "test-key"})
        arr = subject.arr_service()
        assert arr.sources == ("radarr",)
        assert subject.clients() == [subject.radarr_client()]

    def test_profile_source_directory_receives_store_and_limit(self, subject: Container) -> None:
        subject.environment.override({"WARDEN_PROFILES_DIRECTORY": "/profiles", "WARDEN_PROFILES_CACHE_MAX_BYTES": "17"})
        store = Mock(spec=ProfileStore)
        subject.profile_store.override(store)
        source = subject.profile_source()
        assert isinstance(source, DirectoryProfileSource)
        assert source.store is store
        assert source.directory == Path("/profiles")
        assert source.max_bytes == 17
        assert subject.profile_source() is source
        assert not subject.http.initialized

    def test_profile_source_git_receives_registered_git_cache_and_store(self, subject: Container) -> None:
        subject.environment.override({"WARDEN_PROFILES_REPO": "https://example.invalid/profiles", "WARDEN_PROFILES_PATH": "shared"})
        git, cache, store = Mock(spec=GitClient), Mock(spec=SnapshotCache), Mock(spec=ProfileStore)
        subject.git_client.override(git)
        subject.profile_cache.override(cache)
        subject.profile_store.override(store)
        source = subject.profile_source()
        assert isinstance(source, GitProfileSource)
        assert (source.git, source.cache, source.store) == (git, cache, store)
        assert (source.repo, source.ref, source.path) == ("https://example.invalid/profiles", "main", "shared")
        assert subject.profile_source() is source
        cache.prepare.assert_not_called()
        git.checkout.assert_not_called()

    def test_profile_observer_receives_overridden_dependencies(self, subject: Container) -> None:
        source, arr = Mock(spec=ProfileSource), Mock(spec=ArrService)
        subject.profile_source.override(source)
        subject.arr_service.override(arr)
        subject.environment.override({"WARDEN_RADARR_PROFILES": '["HD"]'})
        observer = subject.profile_observer()
        assert isinstance(observer, Observer)
        assert observer.source is source
        assert observer.arr is arr
        assert observer.metrics is subject.metrics()
        assert observer.clock is subject.clock()
        assert observer.selections == {"radarr": '["HD"]'}
        assert observer.emit is subject.profile_emit()
        assert subject.profile_observer() is observer

    def test_profile_store_and_arr_service_ignore_invalid_observer_and_server_settings(self, subject: Container) -> None:
        subject.environment.override({"WARDEN_METRICS_PORT": "invalid", "WARDEN_PROFILES_REPO": "--invalid"})
        assert isinstance(subject.profile_store(), ProfileStore)
        assert (subject.arr_service()).sources == ()
        assert not subject.http.initialized
