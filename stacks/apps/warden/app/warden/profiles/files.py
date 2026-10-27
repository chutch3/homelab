from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import Iterator, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

import yaml
from jsonschema import Draft202012Validator
from yaml.nodes import MappingNode

from warden.profiles.catalog import Document, Snapshot, validate_references
from warden.profiles.storage import require_local_filesystem


class _UniqueSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("mapping keys must be strings")
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


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


def load_catalog(directory: Path, max_bytes: int | None = None) -> tuple[Document, ...]:
    """Read local files without modifying the catalog or contacting Arr."""
    if directory.is_symlink():
        raise ValueError(f"{directory}: symlink catalog roots are unsupported")
    if not directory.is_dir():
        raise ValueError(f"{directory}: catalog directory does not exist")
    schema_dir = Path(__file__).with_name("schemas")
    validators = {
        kind: Draft202012Validator(json.loads((schema_dir / f"{kind}-v1.json").read_text()))
        for kind in ("profiles", "custom_formats")
    }
    documents: list[Document] = []
    remaining = max_bytes
    for source, kind, path in _catalog_paths(directory):
        relative = str(path.relative_to(directory))
        try:
            if remaining is None:
                content = path.read_text(encoding="utf-8")
            else:
                with path.open('rb') as stream:
                    raw = stream.read(remaining + 1)
                remaining -= len(raw)
                if remaining < 0:
                    raise ValueError('catalog byte budget exceeded')
                content = raw.decode('utf-8')
            data = yaml.load(content, Loader=_UniqueSafeLoader)
            errors = list(validators[kind].iter_errors(data))
            if errors:
                details = []
                for error in errors:
                    field = ""
                    for part in error.absolute_path:
                        field += f"[{part}]" if isinstance(part, int) else f".{part}"
                    details.append(f"{field.lstrip('.') or '$'}: {error.message}")
                raise ValueError("; ".join(details))
        except (ValueError, OSError, yaml.YAMLError) as exc:
            raise ValueError(f"{relative}: {exc}") from exc
        documents.append(Document(source, kind, relative, data))
    validate_references(documents)
    return tuple(documents)


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
    for document in documents:
        relative = Path(document.path)
        if relative.is_absolute() or ".." in relative.parts or relative.parts[:2] != (document.source, document.kind):
            raise ValueError(f"{document.path}: invalid catalog path")
    for ancestor in (directory, *directory.parents):
        if ancestor.is_symlink():
            raise ValueError(f"{ancestor}: symlink output paths are unsupported")
    existing = directory
    while not existing.exists():
        existing = existing.parent
    mountinfo = Path("/proc/self/mountinfo").read_text()
    require_local_filesystem(str(existing.resolve()), mountinfo)
    payloads = {
        d.path: (json.dumps(d.data, indent=2, ensure_ascii=False) + "\n" if d.kind == "custom_formats"
                 else yaml.safe_dump(d.data, sort_keys=False, allow_unicode=True)).encode("utf-8")
        for d in documents
    }
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
