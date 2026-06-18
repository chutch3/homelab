from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel


class SearchLedgerRow(SQLModel, table=True):
    __tablename__ = "search_ledger"
    window: str = Field(primary_key=True)
    spent: int = Field(default=0)


class SearchLedgerRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def spent(self, window: str) -> int:
        with Session(self._engine) as session:
            row = session.get(SearchLedgerRow, window)
            return row.spent if row else 0

    def add(self, window: str, n: int) -> None:
        with Session(self._engine) as session:
            row = session.get(SearchLedgerRow, window)
            if row is None:
                row = SearchLedgerRow(window=window, spent=0)
            row.spent += n
            session.add(row)
            session.commit()
