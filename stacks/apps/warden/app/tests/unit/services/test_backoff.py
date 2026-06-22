from datetime import datetime, timedelta, timezone

from warden.services.backoff import BackoffTracker

NOW = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
COOLDOWN = timedelta(days=30)
UNTIL = (NOW + COOLDOWN).timestamp()


def _tracker(threshold: int = 3) -> BackoffTracker:
    # `enabled` is gated by the orchestrator (see test_tick), not by decide() itself.
    return BackoffTracker(enabled=True, threshold=threshold, cooldown=COOLDOWN)


def test_miss_below_threshold_bumps_streak_without_cooldown():
    out = _tracker(threshold=3).decide(streaks={}, hit_ids=[], miss_ids=[7], now=NOW)
    assert out.upsert == {7: (1, 0.0)}        # streak 1, no cooldown
    assert out.entered == 0
    assert out.clear == frozenset()


def test_reaching_threshold_sets_cooldown_and_counts_entered():
    out = _tracker(threshold=3).decide(streaks={7: 2}, hit_ids=[], miss_ids=[7], now=NOW)
    assert out.upsert == {7: (3, UNTIL)}
    assert out.entered == 1


def test_miss_past_threshold_re_sets_cooldown():
    out = _tracker(threshold=3).decide(streaks={7: 5}, hit_ids=[], miss_ids=[7], now=NOW)
    assert out.upsert == {7: (6, UNTIL)}
    assert out.entered == 1


def test_hit_clears_the_item():
    out = _tracker().decide(streaks={7: 9}, hit_ids=[7], miss_ids=[], now=NOW)
    assert out.clear == frozenset({7})
    assert out.upsert == {}


def test_mixed_hits_and_misses():
    out = _tracker(threshold=3).decide(streaks={1: 2, 2: 0}, hit_ids=[3], miss_ids=[1, 2], now=NOW)
    assert out.clear == frozenset({3})
    assert out.upsert == {1: (3, UNTIL), 2: (1, 0.0)}   # 1 crosses, 2 just bumps
    assert out.entered == 1
