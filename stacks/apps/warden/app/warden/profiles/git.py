from __future__ import annotations

import asyncio
import contextlib
import os
import re
import shutil
import signal
from pathlib import Path
from tempfile import mkdtemp

from warden.profiles.catalog import Snapshot
from warden.profiles.files import load_catalog
from warden.profiles.settings import ProfileSettings
from warden.profiles.storage import require_local_filesystem


class GitCatalog:
    """Single-writer disposable snapshots; all mutations are confined to a checked cache."""

    def __init__(self, settings: ProfileSettings) -> None:
        self.settings = settings
        self.current: Snapshot | None = None
        self._active: Path | None = None

    def _prepare(self) -> None:
        cache = self.settings.cache
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
            if entry != self._active:
                shutil.rmtree(entry)

    def _check_budget(self) -> None:
        total = count = 0
        for root, directories, files in os.walk(self.settings.cache, followlinks=False):
            for name in [*directories, *files]:
                try:
                    stat = (Path(root) / name).lstat()
                except FileNotFoundError:
                    continue
                total += max(stat.st_size, stat.st_blocks * 512)
                count += 1
                if total > self.settings.max_bytes or count > 10000:
                    raise ValueError("profile cache budget exceeded")

    async def _run(self, *args: str, cwd: Path | None = None) -> str:
        env = {**os.environ, "TMPDIR": str(self.settings.cache), "GIT_TERMINAL_PROMPT": "0",
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_OPTIONAL_LOCKS": "0",
               "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o StrictHostKeyChecking=yes"}
        process = await asyncio.create_subprocess_exec(
            "git", "-c", "core.hooksPath=/dev/null", "-c", "gc.auto=0", "-c", "protocol.ext.allow=never", *args,
            cwd=cwd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )

        async def read_output() -> bytes:
            output = bytearray()
            while chunk := await process.stdout.read(4096):
                output.extend(chunk)
                if len(output) > 65536:
                    raise ValueError("git response exceeded output budget")
            return bytes(output)

        reader = asyncio.create_task(read_output())
        waiter = asyncio.create_task(process.wait())
        try:
            async with asyncio.timeout(self.settings.timeout):
                while not waiter.done():
                    await asyncio.wait({waiter}, timeout=0.05)
                    await asyncio.to_thread(self._check_budget)
                    if reader.done() and reader.exception():
                        raise reader.exception()
                output = await reader
                await asyncio.to_thread(self._check_budget)
                if process.returncode != 0:
                    raise ValueError("git operation failed; check repository, ref, and credentials")
                return output.decode("utf-8").strip()
        finally:
            if process.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
            await process.wait()
            reader.cancel()
            waiter.cancel()
            await asyncio.gather(reader, waiter, return_exceptions=True)

    async def _resolve(self) -> str:
        ref = self.settings.ref
        if re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", ref):
            return ref.lower()
        patterns = [ref, f"{ref}^{{}}"] if ref.startswith("refs/") else [f"refs/heads/{ref}", f"refs/tags/{ref}", f"refs/tags/{ref}^{{}}"]
        output = await self._run("ls-remote", "--exit-code", "--", self.settings.repo, *patterns)
        refs = {name: sha for sha, name in (line.split() for line in output.splitlines())}
        choices = {name: refs.get(f"{name}^{{}}", sha) for name, sha in refs.items() if not name.endswith("^{}")}
        if len(choices) != 1:
            raise ValueError("repository ref is missing or ambiguous; use refs/heads/ or refs/tags/")
        commit = next(iter(choices.values()))
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
            raise ValueError("invalid commit returned by repository")
        return commit

    async def fetch(self) -> Snapshot:
        await asyncio.to_thread(self._prepare)
        await asyncio.to_thread(self._check_budget)
        commit = await self._resolve()
        if self.current is not None and self.current.commit == commit and self._active.is_dir():
            return self.current
        candidate = Path(mkdtemp(prefix="snapshot-", dir=self.settings.cache))
        try:
            await self._run("init", "--quiet", "--template=", cwd=candidate)
            await self._run("fetch", "--quiet", "--depth=1", "--no-tags", "--", self.settings.repo, commit, cwd=candidate)
            await self._run("checkout", "--quiet", "--detach", "FETCH_HEAD", cwd=candidate)
            if await self._run("rev-parse", "HEAD", cwd=candidate) != commit:
                raise ValueError("repository revision changed during fetch")
            catalog = candidate / self.settings.path
            if not catalog.resolve().is_relative_to(candidate):
                raise ValueError("profile path escapes the repository")
            documents = await asyncio.to_thread(load_catalog, catalog)
            await asyncio.to_thread(self._check_budget)
            previous = self._active
            snapshot = Snapshot(commit, documents)
            self._active, self.current = candidate, snapshot
            if previous is not None:
                await asyncio.to_thread(shutil.rmtree, previous)
            return snapshot
        finally:
            if candidate != self._active:
                await asyncio.to_thread(shutil.rmtree, candidate)
