"""The database every area shares: the engine and its connection pool, the transactions a
service's work is done in, and the declarative base the ORM models are mapped on. Alembic
migrations create and change the tables; nothing here creates them."""

import functools
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Concatenate, Protocol, overload

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


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
    """Application-scoped. It owns the engine and the session factories, never a session: each
    transaction opens its own, so none is shared between them."""

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


class NotInTransaction(RuntimeError):
    """The database was worked on outside a transaction, or written to within a read."""


# The transaction the work in progress is part of (per thread and per task): its session, and
# whether it only reads.
_in_progress: ContextVar[tuple[Session, bool] | None] = ContextVar("transaction", default=None)


def current_session() -> Session:
    """The session of the transaction in progress, which repositories work on."""
    in_progress = _in_progress.get()
    if in_progress is None:
        raise NotInTransaction("The database is worked on only within a transactional method.")
    return in_progress[0]


class Repository:
    """Works on the transaction in progress, and never ends it."""

    @property
    def session(self) -> Session:
        return current_session()


class Transactions:
    """Begins the transactions a service's work is done in."""

    def __init__(self, database: Database) -> None:
        self.database = database

    @contextmanager
    def begin(self, read_only: bool = False) -> Iterator[None]:
        """Work kept when the block ends and none of it when it raises; a read sees one moment
        of the database. Work begun within a transaction is part of it, and a read may be part
        of writing but not writing of a read."""
        in_progress = _in_progress.get()
        if in_progress is not None:
            if in_progress[1] and not read_only:
                raise NotInTransaction("Nothing is written within a read.")
            yield
            return
        opened = self.database.snapshot if read_only else self.database.session
        with opened() as session:
            token = _in_progress.set((session, read_only))
            try:
                yield
                if not read_only:
                    session.commit()
            finally:
                _in_progress.reset(token)


class _Transacting(Protocol):
    transactions: Transactions


type Method[S: _Transacting, **P, R] = Callable[Concatenate[S, P], R]


@overload
def transactional[S: _Transacting, **P, R](method: Method[S, P, R], /) -> Method[S, P, R]: ...
@overload
def transactional[S: _Transacting, **P, R](
    *, read_only: bool = False
) -> Callable[[Method[S, P, R]], Method[S, P, R]]: ...
def transactional[S: _Transacting, **P, R](
    method: Method[S, P, R] | None = None, /, *, read_only: bool = False
) -> Method[S, P, R] | Callable[[Method[S, P, R]], Method[S, P, R]]:
    """A service method done in one transaction of its service's: what it does is kept when it
    returns, and none of it when it raises."""

    def decorate(method: Method[S, P, R]) -> Method[S, P, R]:
        @functools.wraps(method)
        def done(self: S, *args: P.args, **kwargs: P.kwargs) -> R:
            with self.transactions.begin(read_only):
                return method(self, *args, **kwargs)

        return done

    return decorate if method is None else decorate(method)
