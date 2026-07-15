from __future__ import annotations

from typing import Protocol, runtime_checkable

from fiber.domain.models import DumpJob


@runtime_checkable
class DumpEngine(Protocol):
    """Everything engine-specific about producing a dump and probing reachability.

    Implementations are pure (no filesystem/subprocess I/O): DumpRunner owns the
    creds-file write and the subprocess, ConnectivityProbe owns the probe subprocess.
    """

    def build_argv(self, job: DumpJob, out_path: str, creds_path: str | None = None) -> list[str]:
        """The dump command argv, streaming straight to out_path."""
        ...

    def dump_env(self, password: str) -> dict[str, str]:
        """Extra env for the dump process (merged over os.environ)."""
        ...

    def credentials_content(self, password: str) -> str | None:
        """Body of a temp creds file the runner should write, or None if not needed."""
        ...

    def probe_argv(self, job: DumpJob) -> list[str]:
        """A password-free reachability probe argv."""
        ...
