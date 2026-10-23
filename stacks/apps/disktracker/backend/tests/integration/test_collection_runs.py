"""A collector's runs and its word on them: each run registered when it starts, under an id the
collector chooses so that a lost answer can be asked again, its progress and end reported against
that id, and the collector's heartbeat kept apart from any run, since a collector with nothing to
do is still alive. Reading what is due changes nothing."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from api_calls import source_input
from fastapi.testclient import TestClient
from test_persistence import run_sql

from disktracker.main import create_app

COUNTS = {"seen": 0, "recorded": 0, "queued": 0, "ignored": 0, "failed": 0,
          "rechecked": 0, "recheck_failed": 0}  # fmt: skip


def stamp(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def start(client: TestClient, source: str, started_at: datetime, run_id: str | None = None) -> Any:
    body = {"id": run_id or str(uuid4()), "source": source, "started_at": stamp(started_at)}
    return client.post("/api/collection-runs", json=body)


def finish(
    client: TestClient, run_id: str, status: str, finished_at: datetime, **counts: int
) -> Any:
    body = {"status": status, "finished_at": stamp(finished_at), **COUNTS, **counts}
    return client.patch(f"/api/collection-runs/{run_id}", json=body)


def test_a_run_is_registered_as_it_starts_reports_progress_and_ends(subject: TestClient) -> None:
    started = datetime.now(UTC).replace(microsecond=0)
    run_id = str(uuid4())
    begun = start(subject, "goharddrive", started, run_id)
    progress = subject.patch(
        f"/api/collection-runs/{run_id}", json={**COUNTS, "seen": 120, "recorded": 110}
    )
    running = subject.get("/api/collection-runs", params={"status": "running"}).json()
    ended = finish(subject, run_id, "completed", started + timedelta(minutes=5), seen=130,
                   recorded=118, queued=8, ignored=4, rechecked=3)  # fmt: skip
    after = subject.get("/api/collection-runs", params={"source": "goharddrive"}).json()

    assert begun.status_code == 201, begun.text
    assert begun.json() == {
        "id": run_id, "source": "goharddrive", "status": "running",
        "started_at": stamp(started), "updated_at": begun.json()["updated_at"],
        "finished_at": None, "reason": None, **COUNTS, "stop_requested": False,
    }  # fmt: skip
    assert progress.status_code == 200, progress.text
    assert (progress.json()["seen"], progress.json()["status"]) == (120, "running")
    assert [run["id"] for run in running] == [run_id]
    assert ended.status_code == 200, ended.text
    assert ended.json()["status"] == "completed"
    assert ended.json()["finished_at"] == stamp(started + timedelta(minutes=5))
    assert [(run["status"], run["seen"], run["rechecked"]) for run in after] == [
        ("completed", 130, 3)
    ]


def test_starting_or_ending_a_run_again_is_answered_as_the_first_time(subject: TestClient) -> None:
    """A collector that lost the answer asks again under the same run id: the same request
    changes nothing, and a different one is refused."""
    started = datetime.now(UTC).replace(microsecond=0)
    run_id = str(uuid4())
    first = start(subject, "goharddrive", started, run_id)
    again = start(subject, "goharddrive", started, run_id)
    other = start(subject, "serverpartdeals", started, run_id)
    ended = finish(subject, run_id, "failed", started + timedelta(minutes=1), seen=4)
    ended_again = finish(subject, run_id, "failed", started + timedelta(minutes=1), seen=4)
    changed = finish(subject, run_id, "completed", started + timedelta(minutes=1), seen=4)
    more = subject.patch(f"/api/collection-runs/{run_id}", json={**COUNTS, "seen": 9})
    runs = subject.get("/api/collection-runs").json()

    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json() == first.json()
    assert other.status_code == 409, other.text
    assert (ended_again.status_code, ended_again.json()) == (200, ended.json())
    # A run that has ended cannot end another way, or go on.
    assert (changed.status_code, more.status_code) == (409, 409)
    assert [(run["status"], run["seen"]) for run in runs] == [("failed", 4)]


def test_a_run_report_is_refused_before_it_is_kept_and_only_of_a_known_source_or_run(
    subject: TestClient,
) -> None:
    """What a run may say of itself is the schema's (tests/unit/collector/test_schemas.py)."""
    started = datetime.now(UTC)
    run_id = start(subject, "goharddrive", started).json()["id"]
    refused = subject.patch(f"/api/collection-runs/{run_id}", json={**COUNTS, "seen": -1})
    unknown_source = start(subject, "nowhere", started)
    unknown_run = subject.patch(f"/api/collection-runs/{uuid4()}", json=COUNTS)
    [run] = subject.get("/api/collection-runs").json()

    assert refused.status_code == 422
    assert [issue["loc"] for issue in refused.json()["detail"]] == [["body", "seen"]]
    assert (run["status"], run["seen"]) == ("running", 0)
    assert unknown_source.status_code == 422
    assert unknown_source.json()["detail"][0]["loc"] == ["body", "source"]
    assert unknown_run.status_code == 404


def test_a_run_is_told_to_stop_once_its_source_is_asked_and_a_later_run_is_not(
    subject: TestClient,
) -> None:
    started = datetime.now(UTC)
    source = next(s for s in subject.get("/api/sources").json() if s["key"] == "goharddrive")
    run_id = start(subject, "goharddrive", started).json()["id"]
    before = subject.patch(f"/api/collection-runs/{run_id}", json=COUNTS).json()
    asked = subject.post(f"/api/sources/{source['id']}/stop")
    after = subject.patch(f"/api/collection-runs/{run_id}", json=COUNTS).json()
    stopped = finish(subject, run_id, "stopped", started + timedelta(minutes=2)).json()
    later = start(subject, "goharddrive", started + timedelta(hours=8)).json()
    missing = subject.post(f"/api/sources/{uuid4()}/stop")

    assert before["stop_requested"] is False
    assert (asked.status_code, asked.json()["id"]) == (202, source["id"])
    assert after["stop_requested"] is True
    assert stopped["status"] == "stopped"
    assert later["stop_requested"] is False
    assert missing.status_code == 404


def test_a_heartbeat_says_the_collector_is_alive_and_which_runs_it_still_has(
    subject: TestClient,
) -> None:
    """A collector restarted partway through a run never ends it: its heartbeat names the runs
    it has, and any other still marked running is abandoned."""
    started = datetime.now(UTC)
    unheard = subject.get("/api/collector-status").json()
    kept = start(subject, "goharddrive", started).json()["id"]
    lost = start(subject, "serverpartdeals", started).json()["id"]
    beat = subject.put("/api/collector-heartbeat", json={"runs": [kept]})
    during = subject.get("/api/collector-status").json()
    lost_run = subject.patch(f"/api/collection-runs/{lost}", json=COUNTS)
    finish(subject, kept, "completed", started + timedelta(minutes=1))
    idle = subject.put("/api/collector-heartbeat", json={"runs": []})
    after = subject.get("/api/collector-status").json()
    statuses = {run["id"]: run["status"] for run in subject.get("/api/collection-runs").json()}

    assert unheard["seen_at"] is None and unheard["running"] == []
    assert sorted(unheard["waiting"]) == ["goharddrive", "serverpartdeals", "westerndigital"]
    assert beat.status_code == 200, beat.text
    assert [run["id"] for run in during["running"]] == [kept]
    assert started <= datetime.fromisoformat(during["seen_at"]) <= datetime.now(UTC)
    assert lost_run.status_code == 409
    assert statuses == {kept: "completed", lost: "abandoned"}
    # Nothing to do, and alive.
    assert idle.status_code == 200
    assert after["running"] == [] and after["seen_at"] >= during["seen_at"]


def test_a_new_run_of_a_source_abandons_one_still_marked_running(subject: TestClient) -> None:
    started = datetime.now(UTC)
    old = start(subject, "goharddrive", started - timedelta(hours=8)).json()["id"]
    new = start(subject, "goharddrive", started).json()["id"]
    statuses = {run["id"]: run["status"] for run in subject.get("/api/collection-runs").json()}
    assert statuses == {old: "abandoned", new: "running"}


def test_reading_what_is_due_changes_nothing(subject: TestClient) -> None:
    started = datetime.now(UTC)
    run_id = start(subject, "goharddrive", started).json()["id"]
    due = subject.get("/api/sources", params={"due": True})
    status = subject.get("/api/collector-status").json()

    # A source whose run has just started is not due; the run goes on, and nobody was heard.
    assert due.status_code == 200, due.text
    assert sorted(source["key"] for source in due.json()) == ["serverpartdeals", "westerndigital"]
    assert [run["id"] for run in status["running"]] == [run_id]
    assert status["seen_at"] is None


def test_runs_are_read_by_source_by_when_they_ended_or_the_latest_of_each_source(
    database_url: str,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)

    def ended(client: TestClient, source: str, hours_ago: float, status: str = "completed") -> str:
        at = now - timedelta(hours=hours_ago)
        run_id: str = start(client, source, at - timedelta(minutes=10)).json()["id"]
        finish(client, run_id, status, at)
        return run_id

    with TestClient(create_app()) as client:
        old = ended(client, "serverpartdeals", 30)
        earlier = ended(client, "serverpartdeals", 20)
        failed = ended(client, "westerndigital", 6, "failed")
        latest = ended(client, "serverpartdeals", 4)

        def ids(**query: Any) -> list[str]:
            answer = client.get("/api/collection-runs", params=query)
            assert answer.status_code == 200, answer.text
            return [run["id"] for run in answer.json()]

        everything = ids()
        day = ids(finished_since=stamp(now - timedelta(hours=24)))
        spd = ids(source="serverpartdeals")
        newest = ids(latest_per_source=True)
        refused = client.get("/api/collection-runs", params={"status": "paused"}).status_code

    # Oldest first.
    assert everything == [old, earlier, failed, latest]
    assert day == [earlier, failed, latest]
    assert spd == [old, earlier, latest]
    # The latest run of each source, by source.
    assert newest == [latest, failed]
    assert refused == 422


def test_a_source_nothing_is_recorded_under_is_deleted_with_its_runs(subject: TestClient) -> None:
    source = subject.post("/api/sources", json=source_input()).json()
    start(subject, source["key"], datetime.now(UTC))
    deleted = subject.delete(f"/api/sources/{source['id']}")
    again = subject.delete(f"/api/sources/{source['id']}")
    runs = subject.get("/api/collection-runs").json()
    assert (deleted.status_code, again.status_code, runs) == (204, 404, [])


def test_a_run_is_answered_in_utc_the_same_however_the_database_keeps_its_time(
    database_url: str,
) -> None:
    """A retry is answered as the first time, to the character, whatever zone the database
    works in."""
    run_sql(database_url, "DO $$ BEGIN EXECUTE format("
            "'ALTER DATABASE %I SET timezone TO ''America/New_York''', current_database()); END $$")  # fmt: skip
    started = datetime(2026, 9, 27, 8, tzinfo=UTC)
    run_id = str(uuid4())
    with TestClient(create_app()) as client:
        first = start(client, "goharddrive", started, run_id).json()
        again = start(client, "goharddrive", started, run_id).json()
        ended = finish(client, run_id, "completed", started + timedelta(minutes=5)).json()
        ended_again = finish(client, run_id, "completed", started + timedelta(minutes=5)).json()
    assert again == first and ended_again == ended
    assert ended["finished_at"] == "2026-09-27T08:05:00Z"
    assert ended["started_at"] == "2026-09-27T08:00:00Z"


def test_a_run_that_did_not_complete_says_why(subject: TestClient) -> None:
    """A failed run as its collector said; an interrupted one as disktracker found it."""
    started = datetime.now(UTC).replace(microsecond=0)
    cause = "HTTP 503 from https://www.goharddrive.com/sitemap.xml"
    failed = start(subject, "goharddrive", started).json()["id"]
    told = subject.patch(
        f"/api/collection-runs/{failed}",
        json={**COUNTS, "status": "failed", "finished_at": stamp(started), "reason": cause},
    )
    # Its collector restarted, so its heartbeat no longer names the run.
    lost = start(subject, "serverpartdeals", started).json()["id"]
    subject.put("/api/collector-heartbeat", json={"runs": []})
    superseded = start(subject, "westerndigital", started - timedelta(hours=1)).json()["id"]
    start(subject, "westerndigital", started)
    refused = subject.patch(
        f"/api/collection-runs/{superseded}", json={**COUNTS, "reason": "still going"}
    )
    runs = {run["id"]: run for run in subject.get("/api/collection-runs").json()}

    assert told.status_code == 200, told.text
    assert (runs[failed]["status"], runs[failed]["reason"]) == ("failed", cause)
    assert (runs[lost]["status"], runs[lost]["reason"]) == (
        "abandoned",
        "The collector restarted, or stopped working on it, before it ended.",
    )
    assert (runs[superseded]["status"], runs[superseded]["reason"]) == (
        "abandoned",
        "A newer run of this store started before it ended.",
    )
    assert [run["reason"] for run in runs.values() if run["status"] == "running"] == [None]
    assert refused.status_code == 422
