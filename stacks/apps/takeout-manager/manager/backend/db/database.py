from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

import backend.db.models  # noqa: F401 — registers SQLModel tables before create_all


def _add_missing_columns(engine) -> None:
    """SQLModel.metadata.create_all only creates tables that don't exist yet — it
    never alters ones that already do. This grows any pre-existing table to match
    its current model whenever a column has been added since the table was created,
    so a live deployment's DB file doesn't need a separate migration step."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in SQLModel.metadata.tables.values():
            if table.name not in existing_tables:
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                column_type = column.type.compile(engine.dialect)
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {column_type}"))


class Database:
    def __init__(self, url: str) -> None:
        self._engine = create_engine(url)
        self._session_factory = sessionmaker(
            class_=Session, autocommit=False, autoflush=False, bind=self._engine,
        )
        SQLModel.metadata.create_all(self._engine)
        _add_missing_columns(self._engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        session: Session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
