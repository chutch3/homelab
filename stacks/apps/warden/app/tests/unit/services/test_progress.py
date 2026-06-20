from datetime import datetime, timedelta, timezone

from warden.models import QueueItem
from warden.services.progress import Anchor, ProgressTracker

NOW = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)
MB = 1_000_000


def _qi(did, size_left, status="downloading", qid=1, rid=1):
    return QueueItem(id=qid, remote_id=rid, title="t", status=status, error_message="",
                     added=NOW, download_id=did, size_left=size_left)


def _tracker(window_hours=6.0, min_mb=100, enabled=True):
    return ProgressTracker(window_hours=window_hours, min_progress_bytes=min_mb * MB, enabled=enabled)


class TestProgressTracker:
    def test_new_download_is_anchored_no_verdict(self):
        stale, state = _tracker().evaluate([_qi("A", 1000)], {}, NOW)
        assert stale == []
        assert state == {"A": Anchor(1000, NOW)}

    def test_frozen_past_window_is_stale(self):
        prior = {"A": Anchor(1000, NOW - timedelta(hours=7))}
        stale, state = _tracker().evaluate([_qi("A", 1000)], prior, NOW)
        assert [i.download_id for i in stale] == ["A"]
        assert state["A"] == prior["A"]              # anchor held, not advanced

    def test_glacial_progress_is_stale(self):
        prior = {"A": Anchor(1000 * MB, NOW - timedelta(hours=7))}
        stale, _ = _tracker().evaluate([_qi("A", 999 * MB)], prior, NOW)  # 1 MB in 7h < 100 MB
        assert [i.download_id for i in stale] == ["A"]

    def test_healthy_progress_advances_anchor(self):
        prior = {"A": Anchor(1000 * MB, NOW - timedelta(hours=7))}
        stale, state = _tracker().evaluate([_qi("A", 800 * MB)], prior, NOW)  # 200 MB >= 100 MB
        assert stale == []
        assert state["A"] == Anchor(800 * MB, NOW)   # advanced

    def test_frozen_within_window_not_yet_stale(self):
        prior = {"A": Anchor(1000, NOW - timedelta(hours=1))}
        stale, state = _tracker().evaluate([_qi("A", 1000)], prior, NOW)
        assert stale == []
        assert state["A"] == prior["A"]              # held

    def test_paused_and_no_download_id_excluded(self):
        q = [_qi("A", 1000, status="paused"), _qi("", 1000, status="downloadClientUnavailable")]
        stale, state = _tracker().evaluate(q, {}, NOW)
        assert stale == [] and state == {}

    def test_prunes_absent_download_ids(self):
        prior = {"A": Anchor(1000, NOW - timedelta(hours=1)), "B": Anchor(500, NOW)}
        stale, state = _tracker().evaluate([_qi("A", 1000)], prior, NOW)
        assert set(state) == {"A"}                   # B pruned

    def test_disabled_is_noop(self):
        prior = {"A": Anchor(1000, NOW - timedelta(hours=99))}
        stale, state = _tracker(enabled=False).evaluate([_qi("A", 1000)], prior, NOW)
        assert stale == [] and state == {}
