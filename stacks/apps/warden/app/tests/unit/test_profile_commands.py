from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from warden.profiles.catalog import Document
from warden.profiles.commands import ArrProfileReader, CatalogStore, diff_profiles, dump_profiles
from warden.profiles.compare import compare_catalog
from warden.profiles.export import export_documents


@pytest.fixture()
def store() -> CatalogStore:
    return Mock(spec=CatalogStore)


@pytest.fixture()
def reader() -> ArrProfileReader:
    return Mock(spec=ArrProfileReader)


async def test_diff_failed_catalog_read_does_not_contact_arr(store: CatalogStore, reader: ArrProfileReader) -> None:
    store.load.side_effect = ValueError("invalid catalog")
    with pytest.raises(ValueError, match="invalid catalog"):
        await diff_profiles("radarr", Path("/catalog"), None, store, reader)
    reader.read.assert_not_called()


async def test_disabled_diff_does_not_contact_arr_or_compare(store: CatalogStore, reader: ArrProfileReader) -> None:
    store.load.return_value = ()
    compare = Mock(spec=compare_catalog)
    assert await diff_profiles("radarr", Path("/catalog"), [], store, reader, compare) == {
        "source": "radarr", "profiles": [], "changes": [], "conflicts": [],
    }
    reader.read.assert_not_called()
    compare.assert_not_called()


async def test_unknown_selection_fails_before_arr_read(store: CatalogStore, reader: ArrProfileReader) -> None:
    store.load.return_value = ()
    with pytest.raises(ValueError, match="unknown profile 'Missing'"):
        await diff_profiles("radarr", Path("/catalog"), ["Missing"], store, reader)
    reader.read.assert_not_called()


async def test_diff_coordinates_inputs_and_returns_comparison(store: CatalogStore, reader: ArrProfileReader) -> None:
    documents = (Document("radarr", "profiles", "hd.yml", {"quality_profiles": [{"name": "HD"}]}),)
    store.load.return_value = documents
    reader.read.return_value = ([{"name": "remote profile"}], [{"name": "remote format"}])
    compare = Mock(spec=compare_catalog)
    compare.return_value = {"source": "radarr", "profiles": ["HD"], "changes": [], "conflicts": []}
    assert await diff_profiles("radarr", Path("/catalog"), None, store, reader, compare) == compare.return_value
    store.load.assert_called_once_with(Path("/catalog"))
    reader.read.assert_awaited_once_with()
    compare.assert_called_once_with("radarr", documents, [{"name": "remote profile"}], [{"name": "remote format"}], ["HD"])
    store.write.assert_not_called()


async def test_diff_failed_arr_read_does_not_compare(store: CatalogStore, reader: ArrProfileReader) -> None:
    store.load.return_value = (Document("radarr", "profiles", "hd.yml", {"quality_profiles": [{"name": "HD"}]}),)
    reader.read.side_effect = ValueError("Arr unavailable")
    compare = Mock(spec=compare_catalog)
    with pytest.raises(ValueError, match="Arr unavailable"):
        await diff_profiles("radarr", Path("/catalog"), None, store, reader, compare)
    compare.assert_not_called()


async def test_dump_does_not_publish_after_failed_read(store: CatalogStore, reader: ArrProfileReader) -> None:
    reader.read.side_effect = ValueError("Arr unavailable")
    with pytest.raises(ValueError, match="Arr unavailable"):
        await dump_profiles("radarr", Path("/catalog"), [], store, reader)
    store.write.assert_not_called()


async def test_dump_exports_before_publishing(store: CatalogStore, reader: ArrProfileReader) -> None:
    reader.read.return_value = ([], [])
    export = Mock(spec=export_documents)
    documents = (Document("radarr", "profiles", "hd.yml", {}),)
    export.return_value = documents
    assert await dump_profiles("radarr", Path("/catalog"), ["HD"], store, reader, export) == documents
    reader.read.assert_awaited_once_with()
    export.assert_called_once_with("radarr", [], [], ["HD"])
    store.write.assert_called_once_with(Path("/catalog"), documents)


@pytest.mark.parametrize("error", [KeyError("unexpected"), TypeError("wrong type")])
async def test_dump_rejects_unsupported_response_before_publication(store: CatalogStore, reader: ArrProfileReader, error: Exception) -> None:
    reader.read.return_value = ([], [])
    export = Mock(spec=export_documents)
    export.side_effect = error
    with pytest.raises(ValueError, match="unsupported or incomplete profile structure"):
        await dump_profiles("radarr", Path("/catalog"), [], store, reader, export)
    store.write.assert_not_called()


async def test_publication_failure_is_not_a_success(store: CatalogStore, reader: ArrProfileReader) -> None:
    reader.read.return_value = ([], [])
    export = Mock(spec=export_documents)
    export.return_value = ()
    store.write.side_effect = OSError("disk full")
    with pytest.raises(OSError, match="disk full"):
        await dump_profiles("radarr", Path("/catalog"), [], store, reader, export)
