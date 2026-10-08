import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
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
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        config.attributes["database_url"] = url
        command.upgrade(config, "head")
        yield url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
            )
