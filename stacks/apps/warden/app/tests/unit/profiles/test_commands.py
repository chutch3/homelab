from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from warden.profiles.models import ProfileDocument
from warden.arr_service import ArrService
from warden.profiles.files import ProfileStore
from warden.profiles.commands import diff_profiles, dump_profiles
from warden.profiles.compare import compare_profiles
from warden.profiles.export import export_documents


@pytest.fixture()
def store() -> ProfileStore:
    return Mock(spec=ProfileStore)


@pytest.fixture()
def reader() -> ArrService:
    return Mock(spec=ArrService)


async def test_diff_failed_catalog_read_does_not_contact_arr(store: ProfileStore, reader: ArrService) -> None:
    store.load.side_effect = ValueError("invalid catalog")
    with pytest.raises(ValueError, match="invalid catalog"):
        await diff_profiles("radarr", Path("/catalog"), None, store, reader)
    reader.get_profiles.assert_not_called()


async def test_disabled_diff_does_not_contact_arr_or_compare(store: ProfileStore, reader: ArrService) -> None:
    store.load.return_value = ()
    compare = Mock(spec=compare_profiles)
    assert await diff_profiles("radarr", Path("/catalog"), [], store, reader, compare) == {
        "source": "radarr", "profiles": [], "changes": [], "conflicts": [],
    }
    reader.get_profiles.assert_not_called()
    compare.assert_not_called()


async def test_unknown_selection_fails_before_arr_read(store: ProfileStore, reader: ArrService) -> None:
    store.load.return_value = ()
    with pytest.raises(ValueError, match="unknown profile 'Missing'"):
        await diff_profiles("radarr", Path("/catalog"), ["Missing"], store, reader)
    reader.get_profiles.assert_not_called()


async def test_diff_coordinates_inputs_and_returns_comparison(store: ProfileStore, reader: ArrService) -> None:
    documents = (ProfileDocument("radarr", "profiles", "hd.yml", {"quality_profiles": [{"name": "HD"}]}),)
    store.load.return_value = documents
    reader.get_profiles.return_value = ([{"name": "remote profile"}], [{"name": "remote format"}])
    compare = Mock(spec=compare_profiles)
    compare.return_value = {"source": "radarr", "profiles": ["HD"], "changes": [], "conflicts": []}
    assert await diff_profiles("radarr", Path("/catalog"), None, store, reader, compare) == compare.return_value
    store.load.assert_called_once_with(Path("/catalog"))
    reader.get_profiles.assert_awaited_once_with("radarr")
    compare.assert_called_once_with("radarr", documents, [{"name": "remote profile"}], [{"name": "remote format"}], ["HD"])
    store.write.assert_not_called()


async def test_diff_failed_arr_read_does_not_compare(store: ProfileStore, reader: ArrService) -> None:
    store.load.return_value = (ProfileDocument("radarr", "profiles", "hd.yml", {"quality_profiles": [{"name": "HD"}]}),)
    reader.get_profiles.side_effect = ValueError("Arr unavailable")
    compare = Mock(spec=compare_profiles)
    with pytest.raises(ValueError, match="Arr unavailable"):
        await diff_profiles("radarr", Path("/catalog"), None, store, reader, compare)
    compare.assert_not_called()


async def test_dump_does_not_publish_after_failed_read(store: ProfileStore, reader: ArrService) -> None:
    reader.get_profiles.side_effect = ValueError("Arr unavailable")
    with pytest.raises(ValueError, match="Arr unavailable"):
        await dump_profiles("radarr", Path("/catalog"), [], store, reader)
    store.write.assert_not_called()


async def test_dump_exports_before_publishing(store: ProfileStore, reader: ArrService) -> None:
    reader.get_profiles.return_value = ([], [])
    export = Mock(spec=export_documents)
    documents = (ProfileDocument("radarr", "profiles", "hd.yml", {}),)
    export.return_value = documents
    assert await dump_profiles("radarr", Path("/catalog"), ["HD"], store, reader, export) == documents
    reader.get_profiles.assert_awaited_once_with("radarr")
    export.assert_called_once_with("radarr", [], [], ["HD"])
    store.write.assert_called_once_with(Path("/catalog"), documents)


@pytest.mark.parametrize("error", [KeyError("unexpected"), TypeError("wrong type")])
async def test_dump_rejects_unsupported_response_before_publication(store: ProfileStore, reader: ArrService, error: Exception) -> None:
    reader.get_profiles.return_value = ([], [])
    export = Mock(spec=export_documents)
    export.side_effect = error
    with pytest.raises(ValueError, match="unsupported or incomplete profile structure"):
        await dump_profiles("radarr", Path("/catalog"), [], store, reader, export)
    store.write.assert_not_called()


async def test_publication_failure_is_not_a_success(store: ProfileStore, reader: ArrService) -> None:
    reader.get_profiles.return_value = ([], [])
    export = Mock(spec=export_documents)
    export.return_value = ()
    store.write.side_effect = OSError("disk full")
    with pytest.raises(OSError, match="disk full"):
        await dump_profiles("radarr", Path("/catalog"), [], store, reader, export)
