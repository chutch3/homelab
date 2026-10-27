from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from warden.profiles.models import ProfileDocument
from warden.profiles.validation import validate_references
from warden.profiles.storage import require_local_filesystem
from warden.profiles.reading import ProfileFile, ProfileFiles, DocumentCodec, read_profiles, encode_profiles


def _profile_paths(directory: Path) -> Iterator[tuple[Literal["radarr", "sonarr"], Literal["profiles", "custom_formats"], Path]]:
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


class LocalProfileFiles:
    def entries(self, directory: Path) -> Iterator[ProfileFile]:
        if directory.is_symlink():
            raise ValueError(f"{directory}: symlink profile roots are unsupported")
        if not directory.is_dir():
            raise ValueError(f"{directory}: profile directory does not exist")
        for source, kind, path in _profile_paths(directory):
            yield ProfileFile(source, kind, str(path.relative_to(directory)))

    def read(self, directory: Path, entry: ProfileFile, limit: int | None) -> bytes:
        with (directory / entry.path).open("rb") as stream:
            return stream.read() if limit is None else stream.read(limit)


class ProfileStore:
    """Read profile documents and publish validated exports on approved filesystems."""

    def __init__(self, files: ProfileFiles, codec: DocumentCodec) -> None:
        self.files = files
        self.codec = codec

    def load(self, directory: Path, max_bytes: int | None = None) -> tuple[ProfileDocument, ...]:
        for path in (directory, *directory.parents):
            if path.is_symlink():
                raise ValueError("profile directory must not contain symlink paths")
        return read_profiles(directory, self.files, self.codec, validate_references, max_bytes)

    def write(self, directory: Path, documents: Sequence[ProfileDocument]) -> None:
        """Validate a complete staged export before publishing; never overwrite a file."""
        directory = directory.absolute()
        payloads = encode_profiles(documents, self.codec)
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
            for _, _, path in _profile_paths(directory):
                target = stage / path.relative_to(directory)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
            for relative, payload in payloads.items():
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
            self.load(stage)
            for relative, payload in payloads.items():
                target = directory / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    os.link(stage / relative, target)
                except FileExistsError:
                    if target.is_symlink() or target.read_bytes() != payload:
                        raise ValueError(f"{relative}: output collision during publish; export may be partial") from None
