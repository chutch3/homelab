from datetime import datetime, timedelta, timezone

from warden.models import QueueItem
from warden.services.progress import Anchor, ProgressTracker

NOW = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)
MB = 1_000_000


def _qi(did, size_left, status="downloading", qid=1, rid=1):
    return QueueItem(id=qid, remote_id=rid, title="t", status=status, error_message="",
                     added=NOW, download_id=did, size_left=size_left)


def _tracker(window_hours=6.0, tol_mb=0, enabled=True):
    return ProgressTracker(window_hours=window_hours, jitter_tolerance_bytes=tol_mb * MB, enabled=enabled)


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

    def test_any_progress_keeps_alive(self):
        # 1 MB drained over 13h is slow but real — must NOT be flagged (default tol = 0).
        prior = {"A": Anchor(1000 * MB, NOW - timedelta(hours=13))}
        stale, state = _tracker().evaluate([_qi("A", 999 * MB)], prior, NOW)
        assert stale == []
        assert state["A"] == Anchor(999 * MB, NOW)   # any progress advances the clock

    def test_jitter_within_tolerance_treated_as_frozen(self):
        # With an explicit tolerance, sub-tolerance drift counts as no progress.
        prior = {"A": Anchor(1000 * MB, NOW - timedelta(hours=7))}
        stale, _ = _tracker(tol_mb=5).evaluate([_qi("A", 999 * MB)], prior, NOW)  # 1 MB < 5 MB tol
        assert [i.download_id for i in stale] == ["A"]

    def test_frozen_within_window_not_yet_stale(self):
        prior = {"A": Anchor(1000, NOW - timedelta(hours=1))}
        stale, state = _tracker().evaluate([_qi("A", 1000)], prior, NOW)
        assert stale == []
        assert state["A"] == prior["A"]              # held

    def test_paused_and_no_download_id_excluded(self):
        q = [_qi("A", 1000, status="paused"), _qi("", 1000, status="downloadClientUnavailable")]
        stale, state = _tracker().evaluate(q, {}, NOW)
        assert stale == [] and state == {}

    def test_queued_status_excluded_even_past_window(self):
        # a download waiting in a backlogged client (queued) hasn't started, so a flat
        # sizeleft is expected; it must never be flagged, however long it's sat.
        prior = {"Q": Anchor(1000, NOW - timedelta(hours=99))}
        stale, state = _tracker().evaluate([_qi("Q", 1000, status="queued")], prior, NOW)
        assert stale == []
        assert state == {}                           # excluded -> anchor pruned

    def test_prunes_absent_download_ids(self):
        prior = {"A": Anchor(1000, NOW - timedelta(hours=1)), "B": Anchor(500, NOW)}
        stale, state = _tracker().evaluate([_qi("A", 1000)], prior, NOW)
        assert set(state) == {"A"}                   # B pruned

    def test_disabled_is_noop(self):
        prior = {"A": Anchor(1000, NOW - timedelta(hours=99))}
        stale, state = _tracker(enabled=False).evaluate([_qi("A", 1000)], prior, NOW)
        assert stale == [] and state == {}
