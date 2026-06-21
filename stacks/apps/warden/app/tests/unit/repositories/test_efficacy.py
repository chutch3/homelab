from datetime import datetime, timezone

from sqlmodel import SQLModel, create_engine

from warden.repositories.efficacy import SearchAttemptRepository

T0 = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 6, 21, 12, 30, tzinfo=timezone.utc)


def _repo() -> SearchAttemptRepository:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return SearchAttemptRepository(engine)


def test_record_and_read_back_pending():
    repo = _repo()
    repo.record("radarr", [(1, "missing"), (2, "cutoff_unmet")], T0)
    pending = {a.remote_id: a for a in repo.pending("radarr")}
    assert set(pending) == {1, 2}
    assert pending[1].kind == "missing"
    assert pending[1].searched_at == T0
    assert pending[2].kind == "cutoff_unmet"


def test_pending_is_scoped_by_source():
    repo = _repo()
    repo.record("radarr", [(1, "missing")], T0)
    repo.record("sonarr", [(1, "missing")], T0)
    assert [a.remote_id for a in repo.pending("radarr")] == [1]
    assert repo.count("sonarr") == 1


def test_record_upserts_latest_search_time():
    repo = _repo()
    repo.record("radarr", [(1, "missing")], T0)
    repo.record("radarr", [(1, "missing")], T1)
    pending = repo.pending("radarr")
    assert len(pending) == 1
    assert pending[0].searched_at == T1


def test_drop_removes_resolved_only():
    repo = _repo()
    repo.record("radarr", [(1, "missing"), (2, "missing"), (3, "missing")], T0)
    repo.drop("radarr", {1, 3})
    assert sorted(a.remote_id for a in repo.pending("radarr")) == [2]
    assert repo.count("radarr") == 1


def test_drop_empty_is_a_noop():
    repo = _repo()
    repo.record("radarr", [(1, "missing")], T0)
    repo.drop("radarr", set())
    assert repo.count("radarr") == 1
