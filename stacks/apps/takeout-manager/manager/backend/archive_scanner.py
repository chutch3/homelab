from __future__ import annotations

import os

from backend.domain.models import ScannedArchive

ARCHIVE_SUFFIXES = (".tgz", ".zip")


class ArchiveScanner:
    """The single seam over the filesystem: lists takeout archive files on disk."""

    def __init__(self, archives_dir: str) -> None:
        self._archives_dir = archives_dir

    def scan(self) -> list[ScannedArchive]:
        if not os.path.isdir(self._archives_dir):
            return []
        archives: list[ScannedArchive] = []
        with os.scandir(self._archives_dir) as entries:
            for entry in entries:
                if entry.is_file() and entry.name.endswith(ARCHIVE_SUFFIXES):
                    archives.append(
                        ScannedArchive(filename=entry.name, size_bytes=entry.stat().st_size)
                    )
        return archives

    def delete(self, filename: str) -> bool:
        # Only ever touch a plain file directly inside the archives dir — never a
        # path that could escape it.
        if os.sep in filename or (os.altsep and os.altsep in filename):
            return False
        path = os.path.join(self._archives_dir, filename)
        if os.path.isfile(path):
            os.remove(path)
            return True
        return False
