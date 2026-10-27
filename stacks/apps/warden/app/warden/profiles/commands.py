from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

from warden.arr_service import ArrService
from warden.profiles.files import ProfileStore
from warden.profiles.models import ProfileDocument
from warden.profiles.compare import compare_profiles, select_profiles
from warden.profiles.export import export_documents


async def diff_profiles(
    source: Literal["radarr", "sonarr"], directory: Path, selected: Sequence[str] | None,
    store: ProfileStore, arr: ArrService,
    compare: Callable[..., dict[str, Any]] = compare_profiles,
) -> dict[str, Any]:
    documents = store.load(directory)
    names = select_profiles(source, documents, selected)
    if not names:
        return {"source": source, "profiles": [], "changes": [], "conflicts": []}
    profiles, formats = await arr.get_profiles(source)
    try:
        return compare(source, documents, profiles, formats, names)
    except (KeyError, TypeError) as exc:
        raise ValueError("Arr response has an unsupported or incomplete profile structure") from exc


async def dump_profiles(
    source: Literal["radarr", "sonarr"], directory: Path, selected: Sequence[str],
    store: ProfileStore, arr: ArrService,
    export: Callable[..., tuple[ProfileDocument, ...]] = export_documents,
) -> tuple[ProfileDocument, ...]:
    profiles, formats = await arr.get_profiles(source)
    try:
        documents = export(source, profiles, formats, selected)
    except (KeyError, TypeError) as exc:
        raise ValueError("Arr response has an unsupported or incomplete profile structure") from exc
    store.write(directory, documents)
    return documents
