from datetime import datetime, timedelta, timezone

from warden.models import Anchor
from tests.factories import make_progress_repo

NOW = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)



def test_empty_snapshot():
    assert make_progress_repo().snapshot() == {}


def test_replace_and_snapshot_roundtrip():
    repo = make_progress_repo()
    state = {"A": Anchor(1000, NOW), "B": Anchor(500, NOW - timedelta(hours=2))}
    repo.replace(state)
    got = repo.snapshot()
    assert set(got) == {"A", "B"}
    assert got["A"].size_left == 1000
    assert got["A"].at == NOW                       # aware UTC preserved
    assert got["B"].at == NOW - timedelta(hours=2)


def test_replace_prunes_removed_ids():
    repo = make_progress_repo()
    repo.replace({"A": Anchor(1, NOW), "B": Anchor(2, NOW)})
    repo.replace({"A": Anchor(1, NOW)})
    assert set(repo.snapshot()) == {"A"}
