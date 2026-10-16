"""The database every area shares: the engine and its connection pool, the session factory
repositories open their sessions from, and the declarative base the ORM models are mapped on.
Alembic migrations create and change the tables; nothing here creates them."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


# What a repository opens its sessions with: the database's session or snapshot.
SessionFactory = Callable[[], AbstractContextManager[Session]]


def columns(row: Any) -> dict[str, Any]:
    """A model's column values by attribute name."""
    return {attribute.key: getattr(row, attribute.key) for attribute in row.__mapper__.column_attrs}


def by_column(model: Any, values: dict[str, Any]) -> dict[str, Any]:
    """Values by attribute name, by the name of the column each is kept in: what a statement on
    the model's table, rather than the model, takes."""
    return {model.__mapper__.attrs[key].columns[0].name: value for key, value in values.items()}


class Database:
    """Application-scoped. It owns the engine and the session factories, never a session: each
    repository operation opens its own session, so none is shared between operations."""

    def __init__(self, url: str) -> None:
        # Every moment is read back in UTC, whatever zone the database works in, so a time the
        # API returns is written the same whether it was just given or read again.
        self._engine = create_engine(
            url, pool_pre_ping=True, connect_args={"options": "-c timezone=UTC"}
        )
        # Results are returned once their session has committed and closed, so they are never
        # expired and reloaded.
        self._session_factory = sessionmaker(
            bind=self._engine, autoflush=False, expire_on_commit=False
        )
        # A read of several queries that must describe one moment: a read-only transaction that
        # sees one snapshot from its first query to its last, whatever is committed meanwhile.
        self._snapshot_factory = sessionmaker(
            bind=self._engine.execution_options(
                isolation_level="REPEATABLE READ", postgresql_readonly=True
            ),
            autoflush=False,
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        """A session for one operation: what it does is kept when the operation commits, rolled
        back when it raises, and the session is closed either way."""
        session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def snapshot(self) -> Iterator[Session]:
        """A read-only session whose queries all see the same moment of the database."""
        session = self._snapshot_factory()
        try:
            yield session
        finally:
            session.close()

    def dispose(self) -> None:
        """Close every pooled connection, when the application stops."""
        self._engine.dispose()
