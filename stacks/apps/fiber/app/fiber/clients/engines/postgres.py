from __future__ import annotations

import os

from fiber.domain.models import DumpFormat, DumpJob

_FORMAT_FLAG = {DumpFormat.CUSTOM: "c", DumpFormat.DIRECTORY: "d", DumpFormat.PLAIN: "p"}


def select_pg_dump_binary(bindir: str = "/usr/lib/postgresql") -> str:
    """Return the pg_dump for the highest installed major version, or 'pg_dump' if none."""
    majors: list[int] = []
    try:
        for entry in os.scandir(bindir):
            if entry.is_dir():
                try:
                    majors.append(int(entry.name))
                except ValueError:
                    pass
    except FileNotFoundError:
        pass
    if not majors:
        return "pg_dump"
    return f"{bindir}/{max(majors)}/bin/pg_dump"


class PostgresEngine:
    """Dump/probe strategy for PostgreSQL (pg_dump, PGPASSWORD env, pg_isready)."""

    def __init__(self, binary: str | None = None) -> None:
        self._binary = binary if binary is not None else select_pg_dump_binary()

    def build_argv(self, job: DumpJob, out_path: str, creds_path: str | None = None) -> list[str]:
        argv = [self._binary, "-h", job.host, "-p", str(job.port), "-U", job.user,
                "-d", job.dbname, "-F", _FORMAT_FLAG[job.fmt]]
        if job.fmt is DumpFormat.DIRECTORY and job.jobs > 1:
            argv += ["-j", str(job.jobs)]
        argv += list(job.options)
        argv += ["-f", out_path]
        return argv

    def dump_env(self, password: str) -> dict[str, str]:
        return {"PGPASSWORD": password}

    def credentials_content(self, password: str) -> str | None:
        return None

    def probe_argv(self, job: DumpJob) -> list[str]:
        return ["pg_isready", "-h", job.host, "-p", str(job.port), "-U", job.user]
