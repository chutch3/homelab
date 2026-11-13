from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from warden.profiles.models import ProfileDocument


@dataclass(frozen=True)
class ProfileFile:
    source: Literal["radarr", "sonarr"]
    kind: Literal["profiles", "custom_formats"]
    path: str


class ProfileFiles(Protocol):
    def entries(self, directory: Path) -> Iterable[ProfileFile]: ...
    def read(self, directory: Path, entry: ProfileFile, limit: int | None) -> bytes: ...


class DocumentCodec(Protocol):
    def decode(self, entry: ProfileFile, content: bytes) -> ProfileDocument: ...
    def encode(self, document: ProfileDocument) -> bytes: ...


def read_profiles(
    directory: Path, files: ProfileFiles, codec: DocumentCodec,
    validate: Callable[[Sequence[ProfileDocument]], None], max_bytes: int | None = None,
) -> tuple[ProfileDocument, ...]:
    documents = []
    remaining = max_bytes
    for entry in files.entries(directory):
        try:
            content = files.read(directory, entry, None if remaining is None else remaining + 1)
            if remaining is not None:
                remaining -= len(content)
                if remaining < 0:
                    raise ValueError("profile byte budget exceeded")
            documents.append(codec.decode(entry, content))
        except (ValueError, OSError) as exc:
            raise ValueError(f"{entry.path}: {exc}") from exc
    result = tuple(documents)
    validate(result)
    return result


def encode_profiles(documents: Sequence[ProfileDocument], codec: DocumentCodec) -> dict[str, bytes]:
    for document in documents:
        relative = Path(document.path)
        if relative.is_absolute() or ".." in relative.parts or relative.parts[:2] != (document.source, document.kind):
            raise ValueError(f"{document.path}: invalid profile path")
    return {document.path: codec.encode(document) for document in documents}
