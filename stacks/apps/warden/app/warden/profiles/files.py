from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import Iterator, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from warden.profiles.catalog import Document, Snapshot, validate_references
from warden.profiles.storage import require_local_filesystem
from warden.profiles.codec import catalog_codec
from warden.profiles.reading import CatalogFile, CatalogReader, encode_catalog


def _catalog_paths(directory: Path) -> Iterator[tuple[Literal["radarr", "sonarr"], Literal["profiles", "custom_formats"], Path]]:
    for source in ("radarr", "sonarr"):
        app_dir = directory / source
        if app_dir.is_symlink():
            raise ValueError(f"{source}: symlink directories are unsupported")
        for kind in ("profiles", "custom_formats"):
            base = app_dir / kind
            if base.is_symlink():
                raise ValueError(f"{source}/{kind}: symlink directories are unsupported")
            for path in sorted(base.rglob("*")):
                relative = str(path.relative_to(directory))
                if path.is_symlink():
                    raise ValueError(f"{relative}: symlink entries are unsupported")
                if not path.is_file() or path.suffix not in (".yml", ".yaml", ".json"):
                    continue
                yield source, kind, path


class LocalCatalogFiles:
    def entries(self, directory: Path) -> Iterator[CatalogFile]:
        if directory.is_symlink():
            raise ValueError(f"{directory}: symlink catalog roots are unsupported")
        if not directory.is_dir():
            raise ValueError(f"{directory}: catalog directory does not exist")
        for source, kind, path in _catalog_paths(directory):
            yield CatalogFile(source, kind, str(path.relative_to(directory)))

    def read(self, directory: Path, entry: CatalogFile, limit: int | None) -> bytes:
        with (directory / entry.path).open("rb") as stream:
            return stream.read() if limit is None else stream.read(limit)


def load_catalog(directory: Path, max_bytes: int | None = None) -> tuple[Document, ...]:
    """Compose local adapters; catalog coordination is independently testable."""
    return CatalogReader(LocalCatalogFiles(), catalog_codec(), validate_references).load(directory, max_bytes)


class DirectoryCatalog:
    """Read and validate a plain catalog without writing to it or creating a cache."""

    def __init__(self, directory: Path, max_bytes: int = 32 * 1024 * 1024) -> None:
        self.directory = directory
        self.max_bytes = max_bytes

    async def fetch(self) -> Snapshot:
        for path in (self.directory, *self.directory.parents):
            if path.is_symlink():
                raise ValueError('profile directory must not contain symlink paths')
        documents = await asyncio.to_thread(load_catalog, self.directory, self.max_bytes)
        canonical = json.dumps([(doc.path, doc.data) for doc in documents], sort_keys=True, ensure_ascii=False)
        return Snapshot('directory:' + hashlib.sha256(canonical.encode()).hexdigest(), documents)


def write_catalog(directory: Path, documents: Sequence[Document]) -> None:
    """Validate a complete staged export before publishing; never overwrite a file."""
    directory = directory.absolute()
    payloads = encode_catalog(documents, catalog_codec())
    for ancestor in (directory, *directory.parents):
        if ancestor.is_symlink():
            raise ValueError(f"{ancestor}: symlink output paths are unsupported")
    existing = directory
    while not existing.exists():
        existing = existing.parent
    mountinfo = Path("/proc/self/mountinfo").read_text()
    require_local_filesystem(str(existing.resolve()), mountinfo)
    for relative, payload in payloads.items():
        target = directory / relative
        for ancestor in (target, *target.parents):
            if ancestor.is_symlink():
                raise ValueError(f"{ancestor}: symlink output paths are unsupported")
        require_local_filesystem(str(target.resolve()), mountinfo)
        if target.exists() and (not target.is_file() or target.read_bytes() != payload):
            raise ValueError(f"{relative}: output collision; choose another directory or resolve the file in Git")
    with TemporaryDirectory(prefix=".warden-export-", dir=existing) as staging:
        stage = Path(staging)
        for _, _, path in _catalog_paths(directory):
            target = stage / path.relative_to(directory)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
        for relative, payload in payloads.items():
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        load_catalog(stage)
        for relative, payload in payloads.items():
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(stage / relative, target)
            except FileExistsError:
                if target.is_symlink() or target.read_bytes() != payload:
                    raise ValueError(f"{relative}: output collision during publish; export may be partial") from None


class LocalCatalogStore:
    def load(self, directory: Path) -> tuple[Document, ...]:
        return load_catalog(directory)

    def write(self, directory: Path, documents: Sequence[Document]) -> None:
        write_catalog(directory, documents)
