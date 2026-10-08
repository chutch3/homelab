import os
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from playwright.sync_api import Page, sync_playwright
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from sqlalchemy.engine import URL
from testcontainers.community.postgres import PostgresContainer


@pytest.fixture(scope="session")
def database_admin_url() -> Iterator[str]:
    """Use an explicit test server, or own one disposable server for this session."""
    admin_url = os.environ.get("DISKTRACKER_TEST_ADMIN_URL", "").strip()
    if admin_url:
        yield admin_url
        return

    with PostgresContainer("postgres:16-alpine", driver=None) as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def database_url(database_admin_url: str) -> Iterator[str]:
    """Give each test its own database; never migrate or clear an existing database."""
    admin_url = database_admin_url
    database_name = "disktracker_test_" + uuid4().hex
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    params = conninfo_to_dict(make_conninfo(admin_url, dbname=database_name))
    url = URL.create(
        "postgresql+psycopg",
        username=params["user"],
        password=params.get("password"),
        host=params.get("host"),
        port=int(params.get("port", "5432")),
        database=database_name,
    ).render_as_string(hide_password=False)
    try:
        config = Config(str(Path(__file__).parents[2] / "backend" / "alembic.ini"))
        config.attributes["database_url"] = url
        command.upgrade(config, "head")
        yield url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
            )


@pytest.fixture
def application_url(
    database_url: str, tmp_path: Path, request: pytest.FixtureRequest
) -> Iterator[str]:
    """Run both application servers against this test's disposable database."""
    root = Path(__file__).parents[2]
    backend, frontend = root / "backend", root / "frontend"
    processes: list[subprocess.Popen] = []
    ports = []
    for _ in range(2):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            ports.append(listener.getsockname()[1])
    api_port, ui_port = ports
    base_path = getattr(request, "param", "/")
    environment = {
        **os.environ,
        "DISKTRACKER_DATABASE_URL": database_url,
        "DISKTRACKER_BASE_PATH": base_path,
        "DISKTRACKER_ALLOWED_ORIGIN": f"http://127.0.0.1:{ui_port}",
        "DISKTRACKER_API_ORIGIN": f"http://127.0.0.1:{api_port}",
    }
    with (tmp_path / "servers.log").open("w+") as log:
        try:
            for cwd, args in [
                (
                    backend,
                    [
                        ".venv/bin/uvicorn",
                        "disktracker.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(api_port),
                    ],
                ),
                (
                    frontend,
                    [
                        "node",
                        "node_modules/vite/bin/vite.js",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(ui_port),
                        "--strictPort",
                    ],
                ),
            ]:
                processes.append(
                    subprocess.Popen(args, cwd=cwd, env=environment, stdout=log, stderr=log)
                )
            for endpoint in [
                f"http://127.0.0.1:{api_port}/openapi.json",
                f"http://127.0.0.1:{ui_port}{base_path}",
            ]:
                deadline = time.monotonic() + 45
                while True:
                    try:
                        with urlopen(endpoint, timeout=1):
                            break
                    except OSError:
                        if time.monotonic() > deadline or any(
                            p.poll() is not None for p in processes
                        ):
                            log.seek(0)
                            pytest.fail("Test server did not start: " + log.read())
                        time.sleep(0.1)
            yield f"http://127.0.0.1:{ui_port}{base_path}"
        finally:
            for process in processes:
                process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


@pytest.fixture
def page(application_url: str) -> Iterator[Page]:
    """Give a test a fresh browser tab; the application_url fixture owns servers."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--no-sandbox"])
        try:
            yield browser.new_page(base_url=application_url, timezone_id="UTC")
        finally:
            browser.close()
