from datetime import datetime, timedelta, timezone

from warden.models import QueueItem
from warden.services.stale import StaleDetector

NOW = datetime(2026, 6, 18, 12, 0, tzinfo=timezone.utc)


def _item(status="warning", err="The download is stalled with no connections", age_h=72.0, rid=1, qid=10):
    return QueueItem(id=qid, remote_id=rid, title="X", status=status, error_message=err,
                     added=NOW - timedelta(hours=age_h))


class TestStaleDetector:
    def test_stalled_warning_past_grace_is_stale(self):
        v = StaleDetector(grace_hours=48).detect([_item()], NOW)
        assert len(v) == 1 and v[0].reason == "stalled" and v[0].item.remote_id == 1

    def test_failed_status_classifies_error(self):
        v = StaleDetector(grace_hours=48).detect([_item(status="failed", err="import failed")], NOW)
        assert len(v) == 1 and v[0].reason == "error"

    def test_within_grace_is_not_stale(self):
        assert StaleDetector(grace_hours=48).detect([_item(age_h=47.0)], NOW) == []

    def test_warning_without_error_message_is_not_stale(self):
        assert StaleDetector(grace_hours=48).detect([_item(err="")], NOW) == []

    def test_other_statuses_are_not_stale(self):
        items = [_item(status=s) for s in ("downloading", "queued", "completed",
                                           "downloadClientUnavailable", "paused", "delay")]
        assert StaleDetector(grace_hours=48).detect(items, NOW) == []

    def test_added_with_z_suffix_compares_without_typeerror(self):
        added = datetime.fromisoformat("2026-06-15T00:00:00+00:00")
        item = QueueItem(id=1, remote_id=1, title="X", status="warning",
                         error_message="stalled", added=added)
        assert len(StaleDetector(grace_hours=48).detect([item], NOW)) == 1

    def test_empty_queue(self):
        assert StaleDetector(grace_hours=48).detect([], NOW) == []
