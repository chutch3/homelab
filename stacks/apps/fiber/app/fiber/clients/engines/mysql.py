from __future__ import annotations

from fiber.domain.models import DumpFormat, DumpJob


def mysql_defaults_body(password: str) -> str:
    """Body of the mysql --defaults-extra-file (keeps the password off argv/env).

    Written under both [client] (read by mariadb-dump) and [mydumper] (mydumper's own
    group) so one creds file works for either tool; each ignores the other's group.
    """
    return f"[client]\npassword={password}\n[mydumper]\npassword={password}\n"


class MysqlEngine:
    """Dump/probe strategy for MySQL/MariaDB.

    PLAIN dumps via mariadb-dump --result-file (streamed to disk); DIRECTORY dumps via
    mydumper (parallel, multi-file). The password reaches both through a temp
    --defaults-extra-file, never on argv/env.
    """

    def __init__(self, dump_binary: str = "mariadb-dump", mydumper_binary: str = "mydumper",
                 probe_binary: str = "mariadb-admin") -> None:
        self._dump_binary = dump_binary
        self._mydumper_binary = mydumper_binary
        self._probe_binary = probe_binary

    def _conn_flags(self, job: DumpJob, creds_path: str | None) -> list[str]:
        # --defaults-extra-file must be the first option for the mysql client tools.
        return [f"--defaults-extra-file={creds_path}", "-h", job.host, "-P", str(job.port),
                "-u", job.user]

    def build_argv(self, job: DumpJob, out_path: str, creds_path: str | None = None) -> list[str]:
        conn = self._conn_flags(job, creds_path)
        if job.fmt is DumpFormat.DIRECTORY:
            # mydumper writes a directory; -t threads reuse job.jobs. All-flags, no positional.
            # --protocol=tcp: Fiber always dumps DBs over the network, and mydumper otherwise
            # routes a "localhost" host to the local unix socket (which isn't there).
            return [self._mydumper_binary, *conn, "--protocol=tcp", "-B", job.dbname,
                    "-o", out_path, "-t", str(job.jobs), *job.options]
        # PLAIN: options + --result-file MUST precede the <db> positional (trailing words
        # after <db> are parsed as a table list by mariadb-dump).
        return [self._dump_binary, *conn, *job.options, "--result-file", out_path, job.dbname]

    def dump_env(self, password: str) -> dict[str, str]:
        return {}

    def credentials_content(self, password: str) -> str | None:
        return mysql_defaults_body(password)

    def probe_argv(self, job: DumpJob) -> list[str]:
        return [self._probe_binary, "ping", "-h", job.host, "-P", str(job.port), "-u", job.user]
