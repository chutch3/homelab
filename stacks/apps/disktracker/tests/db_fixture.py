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


@pytest.fixture
def database_url() -> Iterator[str]:
    """Give each test its own database; never migrate or clear an existing database."""
    admin_url = os.environ["DISKTRACKER_TEST_ADMIN_URL"]
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
        config = Config(str(Path(__file__).parents[1] / "backend" / "alembic.ini"))
        config.attributes["database_url"] = url
        command.upgrade(config, "head")
        yield url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
            )
