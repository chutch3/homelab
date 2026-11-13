"""The database every area shares: the engine and its connection pool, the session of the
transaction each thread is in, the transactions a service's work is done in, and the declarative
base the ORM models are mapped on. Alembic migrations create and change the tables; nothing here
creates them."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

# A read of several queries that must describe one moment: a read-only transaction that sees one
# snapshot from its first query to its last, whatever is committed meanwhile.
READ = {"isolation_level": "REPEATABLE READ", "postgresql_readonly": True}


class Base(DeclarativeBase):
    pass


def columns(row: Any) -> dict[str, Any]:
    """A model's column values by attribute name."""
    return {attribute.key: getattr(row, attribute.key) for attribute in row.__mapper__.column_attrs}


def by_column(model: Any, values: dict[str, Any]) -> dict[str, Any]:
    """Values by attribute name, by the name of the column each is kept in: what a statement on
    the model's table, rather than the model, takes."""
    return {model.__mapper__.attrs[key].columns[0].name: value for key, value in values.items()}


class Database:
    """Application-scoped: the engine and its pool, and the sessions repositories work on, one
    for each thread's transaction. Nothing works on a session outside a transaction."""

    def __init__(self, url: str) -> None:
        # Every moment is read back in UTC, whatever zone the database works in, so a time the
        # API returns is written the same whether it was just given or read again.
        self._engine = create_engine(
            url, pool_pre_ping=True, connect_args={"options": "-c timezone=UTC"}
        )
        # Results are returned once their transaction has ended, so they are never expired and
        # reloaded.
        self.sessions = scoped_session(
            sessionmaker(
                bind=self._engine, autobegin=False, autoflush=False, expire_on_commit=False
            )
        )

    def dispose(self) -> None:
        """Close every pooled connection, when the application stops."""
        self.sessions.remove()
        self._engine.dispose()


class Transactions:
    """Begins the transactions a service's work is done in."""

    def __init__(self, sessions: scoped_session) -> None:
        self._sessions = sessions

    @contextmanager
    def begin(self, reads: bool = False) -> Iterator[None]:
        """Work kept when the block ends and none of it when it raises; a read sees one moment
        of the database and writes nothing. None is begun within another."""
        try:
            with self._sessions.begin():
                if reads:
                    self._sessions.connection(execution_options=READ)
                yield
        finally:
            self._sessions.remove()
