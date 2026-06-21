from datetime import datetime, timedelta, timezone

from warden.models import GrabEvent, SearchAttempt
from warden.services.efficacy import EfficacyTracker

NOW = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)


def _tracker(minutes: int = 30, enabled: bool = True) -> EfficacyTracker:
    return EfficacyTracker(enabled=enabled, resolve_window=timedelta(minutes=minutes))


def _attempt(rid: int, ago_min: int) -> SearchAttempt:
    return SearchAttempt(remote_id=rid, kind="missing", searched_at=NOW - timedelta(minutes=ago_min))


def _grab(rid: int, indexer: str, ago_min: int, source: str = "UserInvokedSearch") -> GrabEvent:
    return GrabEvent(remote_id=rid, indexer=indexer, at=NOW - timedelta(minutes=ago_min), release_source=source)


def test_grab_after_search_is_a_hit_with_indexer():
    rec = _tracker().reconcile([_attempt(1, ago_min=10)], [_grab(1, "EZTVL", ago_min=5)], NOW)
    assert rec.hits == ("EZTVL",)
    assert rec.misses == 0
    assert rec.resolved == frozenset({1})


def test_rss_grab_does_not_count_as_a_hit():
    # an attempt still within its window whose only grab is RSS -> neither hit nor miss yet
    rec = _tracker().reconcile([_attempt(1, ago_min=5)],
                               [_grab(1, "EZTVL", ago_min=2, source="Rss")], NOW)
    assert rec.hits == () and rec.misses == 0 and rec.resolved == frozenset()


def test_grab_before_the_search_is_ignored():
    # a grab that predates the search can't be its result
    rec = _tracker().reconcile([_attempt(1, ago_min=5)], [_grab(1, "EZTVL", ago_min=20)], NOW)
    assert rec.hits == () and rec.misses == 0 and rec.resolved == frozenset()


def test_no_grab_past_window_is_a_miss():
    rec = _tracker(minutes=30).reconcile([_attempt(1, ago_min=45)], [], NOW)
    assert rec.hits == () and rec.misses == 1 and rec.resolved == frozenset({1})


def test_no_grab_within_window_stays_pending():
    rec = _tracker(minutes=30).reconcile([_attempt(1, ago_min=10)], [], NOW)
    assert rec.hits == () and rec.misses == 0 and rec.resolved == frozenset()


def test_mixed_batch_resolves_independently():
    pending = [_attempt(1, ago_min=10), _attempt(2, ago_min=45), _attempt(3, ago_min=5)]
    grabs = [_grab(1, "Knaben", ago_min=3)]                  # 1 hit, 2 missed (aged), 3 pending
    rec = _tracker(minutes=30).reconcile(pending, grabs, NOW)
    assert rec.hits == ("Knaben",)
    assert rec.misses == 1
    assert rec.resolved == frozenset({1, 2})
