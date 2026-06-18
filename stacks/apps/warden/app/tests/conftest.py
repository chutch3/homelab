from __future__ import annotations

import pytest
from sqlmodel import SQLModel, create_engine

from warden.repositories.ledger import SearchLedgerRepository


@pytest.fixture()
def repo() -> SearchLedgerRepository:
    """A fresh in-memory search ledger, shared by repository and orchestrator tests."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return SearchLedgerRepository(engine)
