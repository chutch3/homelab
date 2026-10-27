from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from warden.profiles.catalog import Document


@dataclass(frozen=True)
class CatalogFile:
    source: Literal["radarr", "sonarr"]
    kind: Literal["profiles", "custom_formats"]
    path: str


class CatalogFiles(Protocol):
    def entries(self, directory: Path) -> Iterable[CatalogFile]: ...
    def read(self, directory: Path, entry: CatalogFile, limit: int | None) -> bytes: ...


class DocumentCodec(Protocol):
    def decode(self, entry: CatalogFile, content: bytes) -> Document: ...
    def encode(self, document: Document) -> bytes: ...


class CatalogReader:
    def __init__(
        self, files: CatalogFiles, codec: DocumentCodec, validate: Callable[[Sequence[Document]], None],
    ) -> None:
        self.files = files
        self.codec = codec
        self.validate = validate

    def load(self, directory: Path, max_bytes: int | None = None) -> tuple[Document, ...]:
        documents = []
        remaining = max_bytes
        for entry in self.files.entries(directory):
            try:
                content = self.files.read(directory, entry, None if remaining is None else remaining + 1)
                if remaining is not None:
                    remaining -= len(content)
                    if remaining < 0:
                        raise ValueError("catalog byte budget exceeded")
                documents.append(self.codec.decode(entry, content))
            except (ValueError, OSError) as exc:
                raise ValueError(f"{entry.path}: {exc}") from exc
        result = tuple(documents)
        self.validate(result)
        return result


def encode_catalog(documents: Sequence[Document], codec: DocumentCodec) -> dict[str, bytes]:
    for document in documents:
        relative = Path(document.path)
        if relative.is_absolute() or ".." in relative.parts or relative.parts[:2] != (document.source, document.kind):
            raise ValueError(f"{document.path}: invalid catalog path")
    return {document.path: codec.encode(document) for document in documents}
