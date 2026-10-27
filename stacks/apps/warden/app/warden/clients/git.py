from __future__ import annotations

import asyncio
import contextlib
import os
import re
import signal
from collections.abc import Callable
from pathlib import Path


class GitClient:
    """Execute bounded Git operations, with cache accounting supplied by the owner."""

    def __init__(self, cache_directory: Path, timeout: float, check_budget: Callable[[], None]) -> None:
        self.cache_directory = cache_directory
        self.timeout = timeout
        self.check_budget = check_budget

    async def _run(self, *args: str, cwd: Path | None = None) -> str:
        env = {**os.environ, "TMPDIR": str(self.cache_directory), "GIT_TERMINAL_PROMPT": "0",
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
            async with asyncio.timeout(self.timeout):
                while not waiter.done():
                    await asyncio.wait({waiter}, timeout=0.05)
                    await asyncio.to_thread(self.check_budget)
                    if reader.done() and reader.exception():
                        raise reader.exception()
                output = await reader
                await asyncio.to_thread(self.check_budget)
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

    async def resolve(self, repo: str, ref: str) -> str:
        if re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", ref):
            return ref.lower()
        patterns = [ref, f"{ref}^{{}}"] if ref.startswith("refs/") else [f"refs/heads/{ref}", f"refs/tags/{ref}", f"refs/tags/{ref}^{{}}"]
        output = await self._run("ls-remote", "--exit-code", "--", repo, *patterns)
        refs = {name: sha for sha, name in (line.split() for line in output.splitlines())}
        choices = {name: refs.get(f"{name}^{{}}", sha) for name, sha in refs.items() if not name.endswith("^{}")}
        if len(choices) != 1:
            raise ValueError("repository ref is missing or ambiguous; use refs/heads/ or refs/tags/")
        commit = next(iter(choices.values()))
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
            raise ValueError("invalid commit returned by repository")
        return commit

    async def checkout(self, repo: str, commit: str, directory: Path) -> None:
        await self._run("init", "--quiet", "--template=", cwd=directory)
        await self._run("fetch", "--quiet", "--depth=1", "--no-tags", "--", repo, commit, cwd=directory)
        await self._run("checkout", "--quiet", "--detach", "FETCH_HEAD", cwd=directory)
        if await self._run("rev-parse", "HEAD", cwd=directory) != commit:
            raise ValueError("repository revision changed during fetch")
