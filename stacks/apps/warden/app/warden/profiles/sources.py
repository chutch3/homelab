from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Protocol

from warden.clients.git import GitClient
from warden.profiles.cache import SnapshotCache
from warden.profiles.files import ProfileStore
from warden.profiles.models import ProfileSnapshot


class ProfileSource(Protocol):
    async def fetch(self) -> ProfileSnapshot: ...


class DirectoryProfileSource:
    """Read local configuration and identify its content without writing a cache."""

    def __init__(self, directory: Path, store: ProfileStore, max_bytes: int = 32 * 1024 * 1024) -> None:
        self.directory = directory
        self.store = store
        self.max_bytes = max_bytes

    async def fetch(self) -> ProfileSnapshot:
        documents = await asyncio.to_thread(self.store.load, self.directory, self.max_bytes)
        canonical = json.dumps([(doc.path, doc.data) for doc in documents], sort_keys=True, ensure_ascii=False)
        return ProfileSnapshot('directory:' + hashlib.sha256(canonical.encode()).hexdigest(), documents)


class GitProfileSource:
    """Adopt a repository revision only after its profile documents validate."""

    def __init__(
        self, repo: str, ref: str, path: str, git: GitClient, cache: SnapshotCache, store: ProfileStore,
    ) -> None:
        self.repo = repo
        self.ref = ref
        self.path = path
        self.git = git
        self.cache = cache
        self.store = store
        self.current: ProfileSnapshot | None = None
        self.active: Path | None = None

    async def fetch(self) -> ProfileSnapshot:
        await asyncio.to_thread(self.cache.prepare, self.active)
        await asyncio.to_thread(self.cache.check)
        commit = await self.git.resolve(self.repo, self.ref)
        if self.current is not None and self.current.commit == commit and self.active is not None:
            if await asyncio.to_thread(self.cache.contains, self.active):
                return self.current
        candidate = self.cache.create()
        try:
            await self.git.checkout(self.repo, commit, candidate)
            directory = await asyncio.to_thread(self.cache.profile_directory, candidate, self.path)
            documents = await asyncio.to_thread(self.store.load, directory)
            await asyncio.to_thread(self.cache.check)
            previous = self.active
            snapshot = ProfileSnapshot(commit, documents)
            self.active, self.current = candidate, snapshot
            if previous is not None:
                await asyncio.to_thread(self.cache.discard, previous)
            return snapshot
        finally:
            if candidate != self.active:
                await asyncio.to_thread(self.cache.discard, candidate)
