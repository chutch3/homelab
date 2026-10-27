from __future__ import annotations

import os
import shutil
from pathlib import Path
from tempfile import mkdtemp

from warden.profiles.storage import require_local_filesystem


class SnapshotCache:
    """Own disposable checkouts within a dedicated, bounded local directory."""

    def __init__(self, directory: Path, max_bytes: int) -> None:
        self.directory = directory
        self.max_bytes = max_bytes

    def prepare(self, active: Path | None) -> None:
        cache = self.directory
        for path in (cache, *cache.parents):
            if path.is_symlink():
                raise ValueError("profile cache must not contain symlink paths")
        if any(cache == root or root in cache.parents for root in (Path("/state"), Path("/mnt/iscsi"))):
            raise ValueError("profile cache must be separate from shared application state")
        existing = cache
        while not existing.exists():
            existing = existing.parent
        require_local_filesystem(str(existing.resolve()), Path("/proc/self/mountinfo").read_text())
        marker = cache / ".warden-profile-cache-v1"
        if cache.exists() and any(cache.iterdir()) and (not marker.is_file() or marker.is_symlink()):
            raise ValueError("profile cache must be a dedicated empty directory")
        cache.mkdir(parents=True, exist_ok=True)
        if not marker.exists():
            marker.touch(mode=0o600, exist_ok=False)
        for entry in cache.iterdir():
            if entry == marker:
                continue
            if not entry.name.startswith("snapshot-") or entry.is_symlink() or not entry.is_dir():
                raise ValueError("unexpected files in dedicated profile cache")
            if entry != active:
                shutil.rmtree(entry)

    def check(self) -> None:
        total = count = 0
        for root, directories, files in os.walk(self.directory, followlinks=False):
            for name in [*directories, *files]:
                try:
                    stat = (Path(root) / name).lstat()
                except FileNotFoundError:
                    continue
                total += max(stat.st_size, stat.st_blocks * 512)
                count += 1
                if total > self.max_bytes or count > 10000:
                    raise ValueError("profile cache budget exceeded")

    def create(self) -> Path:
        return Path(mkdtemp(prefix="snapshot-", dir=self.directory))

    def contains(self, candidate: Path) -> bool:
        return candidate.is_dir()

    def profile_directory(self, candidate: Path, relative: str) -> Path:
        directory = candidate / relative
        if not directory.resolve().is_relative_to(candidate):
            raise ValueError("profile path escapes the repository")
        return directory

    def discard(self, candidate: Path) -> None:
        try:
            shutil.rmtree(candidate)
        except FileNotFoundError:
            pass
