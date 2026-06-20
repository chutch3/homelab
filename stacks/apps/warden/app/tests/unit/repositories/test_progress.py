from datetime import datetime, timedelta, timezone

from sqlmodel import SQLModel, create_engine

from warden.models import Anchor
from warden.repositories.progress import QueueProgressRepository

NOW = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)


def _repo() -> QueueProgressRepository:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return QueueProgressRepository(engine)


def test_empty_snapshot():
    assert _repo().snapshot() == {}


def test_replace_and_snapshot_roundtrip():
    repo = _repo()
    state = {"A": Anchor(1000, NOW), "B": Anchor(500, NOW - timedelta(hours=2))}
    repo.replace(state)
    got = repo.snapshot()
    assert set(got) == {"A", "B"}
    assert got["A"].size_left == 1000
    assert got["A"].at == NOW                       # aware UTC preserved
    assert got["B"].at == NOW - timedelta(hours=2)


def test_replace_prunes_removed_ids():
    repo = _repo()
    repo.replace({"A": Anchor(1, NOW), "B": Anchor(2, NOW)})
    repo.replace({"A": Anchor(1, NOW)})
    assert set(repo.snapshot()) == {"A"}
