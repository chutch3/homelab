from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fiber.domain.models import BowlEntry

_PARTIAL = ".partial"


class BowlStorage:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def _dir(self, service: str) -> Path:
        d = self._root / service
        d.mkdir(parents=True, exist_ok=True)
        return d

    def temp_path(self, service: str, timestamp: str, ext: str) -> str:
        return str(self._dir(service) / f"{timestamp}.{ext}{_PARTIAL}")

    def promote(self, temp_path: str) -> str:
        final = temp_path[: -len(_PARTIAL)]
        # Ensure the temp file exists (handle empty files)
        Path(temp_path).touch(exist_ok=True)
        os.replace(temp_path, final)
        return final

    def has_room(self, required_bytes: int) -> bool:
        self._root.mkdir(parents=True, exist_ok=True)
        return shutil.disk_usage(self._root).free >= required_bytes

    def usage(self) -> tuple[int, int]:
        """Return (used_bytes, free_bytes) for the bowl root."""
        self._root.mkdir(parents=True, exist_ok=True)
        used = sum(
            f.stat().st_size
            for f in self._root.rglob("*")
            if f.is_file()
        )
        free = shutil.disk_usage(self._root).free
        return used, free

    def size(self, path: str) -> int:
        p = Path(path)
        if p.is_dir():
            return sum(f.stat().st_size for _, f in _walk_files(p))
        return p.stat().st_size

    def checksum(self, path: str) -> str:
        h = hashlib.sha256()
        p = Path(path)
        if p.is_dir():
            for _, f in _walk_files(p):
                with f.open("rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(chunk)
        else:
            with p.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
        return h.hexdigest()

    def list_entries(self, service: str) -> list[BowlEntry]:
        entries: list[BowlEntry] = []
        for p in self._dir(service).iterdir():
            if p.name.endswith(".manifest.json"):
                continue
            stat = p.stat()
            entries.append(BowlEntry(
                path=str(p),
                size_bytes=self.size(str(p)),
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                is_temp=p.name.endswith(_PARTIAL),
            ))
        return entries

    def write_receipt(self, final_path: str, manifest: dict[str, object]) -> str:
        receipt = f"{final_path}.manifest.json"
        Path(receipt).write_text(json.dumps(manifest, indent=2))
        return receipt

    def write_sample(self, service: str, timestamp: str, text: str) -> str:
        sample = self._dir(service) / f"{timestamp}.stool.log"
        sample.write_text(text)
        return str(sample)

    def read_text(self, path: str) -> str | None:
        p = Path(path)
        try:
            return p.read_text()
        except (FileNotFoundError, OSError):
            return None

    def delete(self, path: str) -> None:
        p = Path(path)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)


def _walk_files(root: Path) -> list[tuple[str, Path]]:
    """Return (relative_path_str, absolute_Path) for all files under root, sorted by rel path."""
    results: list[tuple[str, Path]] = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            abs_p = Path(dirpath) / name
            rel = str(abs_p.relative_to(root))
            results.append((rel, abs_p))
    results.sort(key=lambda t: t[0])
    return results
