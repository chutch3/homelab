from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol

from warden.profiles.catalog import Document
from warden.profiles.compare import compare_catalog, select_profiles
from warden.profiles.export import export_documents


class CatalogStore(Protocol):
    def load(self, directory: Path) -> tuple[Document, ...]: ...
    def write(self, directory: Path, documents: Sequence[Document]) -> None: ...


class ArrProfileReader(Protocol):
    async def read(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]: ...


async def diff_profiles(
    source: Literal["radarr", "sonarr"], directory: Path, selected: Sequence[str] | None,
    store: CatalogStore, reader: ArrProfileReader,
    compare: Callable[..., dict[str, Any]] = compare_catalog,
) -> dict[str, Any]:
    documents = store.load(directory)
    names = select_profiles(source, documents, selected)
    if not names:
        return {"source": source, "profiles": [], "changes": [], "conflicts": []}
    profiles, formats = await reader.read()
    try:
        return compare(source, documents, profiles, formats, names)
    except (KeyError, TypeError) as exc:
        raise ValueError("Arr response has an unsupported or incomplete profile structure") from exc


async def dump_profiles(
    source: Literal["radarr", "sonarr"], directory: Path, selected: Sequence[str],
    store: CatalogStore, reader: ArrProfileReader,
    export: Callable[..., tuple[Document, ...]] = export_documents,
) -> tuple[Document, ...]:
    profiles, formats = await reader.read()
    try:
        documents = export(source, profiles, formats, selected)
    except (KeyError, TypeError) as exc:
        raise ValueError("Arr response has an unsupported or incomplete profile structure") from exc
    store.write(directory, documents)
    return documents
