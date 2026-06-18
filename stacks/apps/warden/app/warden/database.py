from __future__ import annotations

from sqlmodel import SQLModel, create_engine
from sqlalchemy.engine import Engine


def make_engine(url: str) -> Engine:
    engine = create_engine(url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine
