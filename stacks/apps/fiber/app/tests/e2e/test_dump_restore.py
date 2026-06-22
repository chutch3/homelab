"""Black-box e2e: run the real fiber image against a seeded Postgres, let it
produce a dump, restore that dump into a scratch Postgres, and assert the row
count round-trips.

Drives the compose stack in this directory via the docker CLI (unprivileged,
bridge network — no swarm). Consumes a prebuilt image via ``$FIBER_IMAGE`` (set
by CI to the pipeline-built image); falls back to building ``fiber:e2e`` locally
for dev runs. This is the pytest replacement for the old ``run-e2e.sh``.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

HERE = Path(__file__).parent
STACK_ROOT = HERE.parents[2]  # app/tests/e2e -> app/tests -> app -> stacks/apps/fiber
PROJECT = "fiber-e2e"
COMPOSE = ["docker", "compose", "-p", PROJECT, "-f", str(HERE / "compose.yml")]
RESTORE = "fiber-e2e-restore"
EXPECTED_ROWS = "1000"


def _run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


@pytest.fixture(scope="module")
def stack():
    # The compose mounts this file as fiber's /run/secrets/e2e_db_password.
    (HERE / "e2e_db_password").write_text("e2e_password")
    env = dict(os.environ)
    if not env.get("FIBER_IMAGE"):
        # Dev fallback: build the image the compose expects (CI sets FIBER_IMAGE instead).
        _run(
            [
                "docker", "build", "-t", "fiber:e2e",
                "-f", str(STACK_ROOT / "app" / "Dockerfile"), str(STACK_ROOT),
            ]
        )
    try:
        _run(COMPOSE + ["up", "-d"], env=env)
        yield
    finally:
        subprocess.run(COMPOSE + ["down", "-v", "--remove-orphans"], check=False)
        subprocess.run(["docker", "rm", "-f", RESTORE], check=False)
        (HERE / "e2e_db_password").unlink(missing_ok=True)
        (HERE / "_e2e.dump").unlink(missing_ok=True)


def _wait_for_dump(timeout: int = 120) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            COMPOSE + ["exec", "-T", "fiber", "sh", "-c", "ls /backups/*/*.dump 2>/dev/null | head -1"],
            capture_output=True, text=True,
        )
        dump = result.stdout.strip()
        if dump:
            return dump
        time.sleep(3)
    return ""


def _wait_ready(timeout: int = 30) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if subprocess.run(["docker", "exec", RESTORE, "pg_isready", "-U", "postgres"]).returncode == 0:
            return
        time.sleep(1)
    raise AssertionError("scratch postgres never became ready")


def test_dump_then_restore_roundtrips_rows(stack):
    dump = _wait_for_dump()
    assert dump, "fiber produced no dump within the timeout"

    # Restore into a scratch postgres on the same network and assert the row count.
    network = f"{PROJECT}_fibernet"
    _run(["docker", "run", "-d", "--name", RESTORE, "--network", network,
          "-e", "POSTGRES_PASSWORD=restore", "postgres:16"])
    _wait_ready()
    _run(["docker", "exec", RESTORE, "psql", "-U", "postgres", "-c", "CREATE DATABASE e2e;"])

    dump_bytes = subprocess.run(
        COMPOSE + ["exec", "-T", "fiber", "cat", dump], capture_output=True, check=True
    ).stdout
    (HERE / "_e2e.dump").write_bytes(dump_bytes)
    _run(["docker", "cp", str(HERE / "_e2e.dump"), f"{RESTORE}:/tmp/e2e.dump"])
    _run(["docker", "exec", RESTORE, "pg_restore", "-U", "postgres", "-d", "e2e",
          "--no-owner", "--no-privileges", "/tmp/e2e.dump"])

    count = subprocess.run(
        ["docker", "exec", RESTORE, "psql", "-U", "postgres", "-d", "e2e",
         "-tAc", "SELECT count(*) FROM e2e_data;"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert count == EXPECTED_ROWS
