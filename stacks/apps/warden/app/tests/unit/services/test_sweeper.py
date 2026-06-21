from datetime import datetime, timedelta, timezone

from warden.models import QueueItem
from warden.services.stale import StaleDetector, StaleVerdict
from warden.services.sweeper import QueueSweeper

NOW = datetime(2026, 6, 18, 12, 0, tzinfo=timezone.utc)


def _stale(rid, qid):
    return QueueItem(id=qid, remote_id=rid, title="X", status="warning",
                     error_message="stalled with no connections", added=NOW - timedelta(hours=72))


def _unavailable(rid, qid):
    return QueueItem(id=qid, remote_id=rid, title="U", status="downloadClientUnavailable",
                     error_message="", added=NOW - timedelta(hours=72))


def _ok(rid, qid):
    return QueueItem(id=qid, remote_id=rid, title="D", status="downloading",
                     error_message="", added=NOW - timedelta(hours=1))


def _sweeper(**over):
    opts = dict(enabled=True, max_removals_per_tick=5, mass_fraction=0.5, min_queue_for_guard=3)
    opts.update(over)
    return QueueSweeper(StaleDetector(grace_hours=48), **opts)


class TestQueueSweeper:
    def test_removes_stale_up_to_cap(self):
        # 8 stale + 9 healthy = 47% < 50% guard -> cap (5) applies, not the bail
        queue = [_stale(i, 100 + i) for i in range(8)] + [_ok(50 + i, 200 + i) for i in range(9)]
        d = _sweeper().plan(queue, NOW)
        assert not d.skipped
        assert len(d.to_remove) == 5
        assert d.stalled_count == 8
        assert d.queue_size == 17
        a = d.to_remove[0]
        assert a.reason == "stalled" and a.age_hours == 72.0
        assert d.all_queued_remote_ids == frozenset(list(range(8)) + list(range(50, 59)))

    def test_mass_unavailable_bails(self):
        # the guard keys on the OUTAGE signal: majority downloadClientUnavailable -> skip
        queue = [_unavailable(1, 11), _unavailable(2, 12), _unavailable(3, 13),
                 _stale(4, 14), _ok(5, 15)]                          # 3 unavailable of 5 = 60% > 50%
        d = _sweeper().plan(queue, NOW)
        assert d.skipped and d.to_remove == ()
        assert d.all_queued_remote_ids == frozenset({1, 2, 3, 4, 5})

    def test_many_stale_but_few_unavailable_does_not_bail(self):
        # genuinely-stuck downloads (client up) must NOT trip the guard, even at >50% of the queue
        queue = [_stale(1, 11), _stale(2, 12), _stale(3, 13), _stale(4, 14), _ok(5, 15)]  # 80% stale, 0 unavailable
        d = _sweeper().plan(queue, NOW)
        assert not d.skipped
        assert len(d.to_remove) == 4

    def test_live_example_under_threshold_cleans(self):
        # 7 unavailable of 59 = 12% < 50% -> not skipped, cap applies
        queue = ([_stale(i, 100 + i) for i in range(13)]
                 + [_unavailable(900 + i, 300 + i) for i in range(7)]
                 + [_ok(500 + i, 400 + i) for i in range(39)])
        d = _sweeper().plan(queue, NOW)
        assert not d.skipped and len(d.to_remove) == 5

    def test_min_queue_floor_disables_guard_on_small_queues(self):
        # 1 stale of 2 = 50% but queue < min_queue_for_guard(3) -> guard off, removes it
        d = _sweeper().plan([_stale(1, 11), _ok(2, 12)], NOW)
        assert not d.skipped and len(d.to_remove) == 1

    def test_merges_extra_verdicts_deduped_by_queue_id(self):
        queue = [_stale(1, 11), _ok(2, 12)]                       # 11 stale-by-status; 12 healthy
        extra = [StaleVerdict(_ok(2, 12), "no_progress"),        # 12 flagged by no-progress
                 StaleVerdict(_stale(1, 11), "no_progress")]     # 11 already a status verdict -> dedup
        d = _sweeper().plan(queue, NOW, extra=extra)
        actions = {a.queue_id: a.reason for a in d.to_remove}
        assert set(actions) == {11, 12}                          # both removed, 11 only once
        assert actions[11] == "stalled"                          # status verdict kept on dedup
        assert actions[12] == "no_progress"

    def test_disabled_removes_nothing_but_keeps_exclusion(self):
        d = _sweeper(enabled=False).plan([_stale(1, 11), _ok(2, 12)], NOW)
        assert not d.skipped and d.to_remove == ()
        assert d.all_queued_remote_ids == frozenset({1, 2})
        assert d.stalled_count == 1
