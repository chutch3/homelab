from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

import fiber.db.models  # noqa: F401 — registers SQLModel tables before create_all


class Database:
    def __init__(self, url: str) -> None:
        self._engine = create_engine(url)
        self._session_factory = sessionmaker(
            class_=Session, autocommit=False, autoflush=False, bind=self._engine,
        )
        SQLModel.metadata.create_all(self._engine)

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
