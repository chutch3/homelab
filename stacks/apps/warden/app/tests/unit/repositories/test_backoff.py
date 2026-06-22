from datetime import datetime, timezone

from sqlmodel import SQLModel, create_engine

from warden.repositories.backoff import SearchBackoffRepository

NOW = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc).timestamp()
FUTURE = NOW + 1000
PAST = NOW - 1000


def _repo() -> SearchBackoffRepository:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return SearchBackoffRepository(engine)


def test_streaks_for_no_ids_is_empty():
    assert _repo().streaks("radarr", []) == {}


def test_write_and_read_streaks():
    repo = _repo()
    repo.write("radarr", clear=frozenset(), upsert={1: (2, 0.0), 2: (3, FUTURE)})
    assert repo.streaks("radarr", [1, 2, 3]) == {1: 2, 2: 3}   # 3 absent -> omitted


def test_write_upserts_existing_rows():
    repo = _repo()
    repo.write("radarr", clear=frozenset(), upsert={1: (1, 0.0)})
    repo.write("radarr", clear=frozenset(), upsert={1: (2, FUTURE)})
    assert repo.streaks("radarr", [1]) == {1: 2}


def test_clear_removes_rows():
    repo = _repo()
    repo.write("radarr", clear=frozenset(), upsert={1: (5, FUTURE)})
    repo.write("radarr", clear=frozenset({1}), upsert={})
    assert repo.streaks("radarr", [1]) == {}


def test_active_returns_only_unexpired_cooldowns():
    repo = _repo()
    repo.write("radarr", clear=frozenset(),
               upsert={1: (3, FUTURE), 2: (3, PAST), 3: (1, 0.0)})  # 1 active, 2 expired, 3 inactive
    assert repo.active("radarr", NOW) == {1}
    assert repo.count_active("radarr", NOW) == 1


def test_active_is_scoped_by_source():
    repo = _repo()
    repo.write("radarr", clear=frozenset(), upsert={1: (3, FUTURE)})
    repo.write("sonarr", clear=frozenset(), upsert={1: (3, FUTURE)})
    assert repo.active("sonarr", NOW) == {1}
    assert repo.count_active("radarr", NOW) == 1
