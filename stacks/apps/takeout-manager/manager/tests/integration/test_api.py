import sqlite3

import pytest
from backend.containers import ManagerContainer
from backend.db.database import Database
from backend.application import create_app
from fastapi.testclient import TestClient
from backend.models import JobStatus, ChunkStatus

pytestmark = pytest.mark.integration


class TestJobAPI:
    @pytest.fixture
    def container_fixture(self):
        return ManagerContainer()

    @pytest.fixture
    def db_connection_fixture(self, container_fixture, tmp_path):
        db_file = tmp_path / "test.db"
        db = Database(url=f"sqlite:///{db_file}")
        with container_fixture.database.override(db):
            # A separate raw connection for test assertions, decoupled from
            # whatever ORM the app uses internally to talk to the same file.
            conn = sqlite3.connect(str(db_file))
            conn.row_factory = sqlite3.Row
            yield conn
            conn.close()

    @pytest.fixture
    def client_fixture(self, container_fixture, db_connection_fixture):
        app = create_app(container_fixture)
        with TestClient(app) as c:
            yield c

    def test_create_job_and_get_next_task(self, client_fixture, db_connection_fixture):
        job_data = {
            "job_id": "test-job-123",
            "user_id": "test-user-456",
            "timestamp": "20240101T000000",
            "auth_user": "0",
            "cookie": "test-cookie-789",
            "total_chunks": 5,
        }
        response = client_fixture.post("/api/jobs", json=job_data)
        assert response.status_code == 200, response.text
        assert (
            response.json()["message"]
            == "Job created successfully and 5 chunks queued."
        )

        response = client_fixture.get("/api/tasks/next")
        task = response.json()

        assert response.status_code == 200
        assert task["id"] == 1
        assert task["type"] == "download"
        assert task["params"]["job_id"] == "test-job-123"
        assert task["params"]["chunk_index"] == 1
        assert task["params"]["cookie"] == "test-cookie-789"

    def test_update_task_status_completes_chunk(self, client_fixture, db_connection_fixture):
        job_data = {
            "job_id": "test-job-update",
            "user_id": "test-user-update",
            "timestamp": "20240101T000000",
            "auth_user": "0",
            "cookie": "test-cookie-update",
            "total_chunks": 1
        }
        client_fixture.post("/api/jobs", json=job_data)

        task_response = client_fixture.get("/api/tasks/next")
        task = task_response.json()
        task_id = task["id"]

        status_data = {"status": ChunkStatus.DOWNLOADED.value, "message": "Chunk downloaded successfully"}
        response = client_fixture.post(f"/api/tasks/{task_id}/status", json=status_data)
        assert response.status_code == 200
        assert response.json()["message"] == "Status received"

        cursor = db_connection_fixture.cursor()
        cursor.execute("SELECT status, message FROM chunks WHERE id = ?", (task_id,))
        updated_chunk = cursor.fetchone()

        assert updated_chunk is not None
        assert updated_chunk["status"] == ChunkStatus.DOWNLOADED.value
        assert updated_chunk["message"] == "Chunk downloaded successfully"

    def test_get_next_task_returns_none_when_no_jobs(self, client_fixture, db_connection_fixture):
        response = client_fixture.get("/api/tasks/next")
        assert response.status_code == 200
        assert response.json() == {"task": "none"}

    def test_job_status_updates_on_chunk_completion(self, client_fixture, db_connection_fixture):
        job_data = {
            "job_id": "test-job-status-update",
            "user_id": "test-user-status",
            "timestamp": "20240102T000000",
            "auth_user": "0",
            "cookie": "test-cookie-status",
            "total_chunks": 2
        }
        client_fixture.post("/api/jobs", json=job_data)

        conn = db_connection_fixture
        cursor = conn.cursor()
        cursor.execute("SELECT id, status FROM jobs WHERE job_id = ?", ("test-job-status-update",))
        job = cursor.fetchone()
        assert job is not None
        assert job["status"] == JobStatus.PENDING.value
        job_id = job["id"]

        task1_response = client_fixture.get("/api/tasks/next")
        task1 = task1_response.json()
        assert task1["params"]["chunk_index"] == 1
        client_fixture.post(f"/api/tasks/{task1['id']}/status", json={"status": ChunkStatus.DOWNLOADED.value, "message": "Chunk 1 done"})

        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        job_status_after_first_chunk = cursor.fetchone()["status"]
        assert job_status_after_first_chunk == JobStatus.IN_PROGRESS.value

        task2_response = client_fixture.get("/api/tasks/next")
        task2 = task2_response.json()
        assert task2["params"]["chunk_index"] == 2
        client_fixture.post(f"/api/tasks/{task2['id']}/status", json={"status": ChunkStatus.DOWNLOADED.value, "message": "Chunk 2 done"})

        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        job_status_after_all_chunks = cursor.fetchone()["status"]
        assert job_status_after_all_chunks == JobStatus.IN_PROGRESS.value

    def test_metadata_task_is_assigned_once_job_completes_and_reports_back(
        self, client_fixture, db_connection_fixture
    ):
        job_data = {
            "job_id": "test-job-metadata",
            "user_id": "test-user-metadata",
            "timestamp": "20240109T000000",
            "auth_user": "0",
            "cookie": "test-cookie-metadata",
            "total_chunks": 1,
        }
        client_fixture.post("/api/jobs", json=job_data)

        conn = db_connection_fixture
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE job_id = ?", ("test-job-metadata",))
        job_id = cursor.fetchone()["id"]

        task = client_fixture.get("/api/tasks/next").json()
        assert task["type"] == "download"  # no metadata task before chunks are done
        client_fixture.post(
            f"/api/tasks/{task['id']}/status",
            json={"status": ChunkStatus.DOWNLOADED.value, "message": "done"},
        )
        extract_task = client_fixture.get("/api/tasks/next").json()
        assert extract_task["type"] == "extract"
        assert extract_task["id"] == job_id
        assert extract_task["params"]["job_id"] == "test-job-metadata"
        assert extract_task["params"]["timestamp"] == "20240109T000000"
        assert extract_task["params"]["total_chunks"] == 1

        cursor.execute("SELECT metadata_status FROM jobs WHERE id = ?", (job_id,))
        assert cursor.fetchone()["metadata_status"] == "processing"

        # Claimed — not offered again while in flight.
        assert client_fixture.get("/api/tasks/next").json() == {"task": "none"}

        response = client_fixture.post(
            f"/api/jobs/{job_id}/metadata-status",
            json={"status": "completed", "message": "Embedded EXIF for 42 files"},
        )
        assert response.status_code == 200

        cursor.execute("SELECT status, metadata_status, metadata_message FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        assert row["status"] == JobStatus.COMPLETED.value
        assert row["metadata_status"] == "completed"
        assert row["metadata_message"] == "Embedded EXIF for 42 files"

    def test_reprocess_metadata_redrives_just_the_metadata_phase(
        self, client_fixture, db_connection_fixture
    ):
        """Manual re-drive: resets only the metadata phase, regardless of its
        current state, without touching already-completed download/extract work."""
        job_data = {
            "job_id": "test-job-redrive",
            "user_id": "test-user-redrive",
            "timestamp": "20240110T000000",
            "auth_user": "0",
            "cookie": "test-cookie-redrive",
            "total_chunks": 1,
        }
        client_fixture.post("/api/jobs", json=job_data)

        conn = db_connection_fixture
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE job_id = ?", ("test-job-redrive",))
        job_id = cursor.fetchone()["id"]

        task = client_fixture.get("/api/tasks/next").json()
        client_fixture.post(
            f"/api/tasks/{task['id']}/status",
            json={"status": ChunkStatus.DOWNLOADED.value, "message": "done"},
        )
        client_fixture.get("/api/tasks/next")  # claim the extract pass
        client_fixture.post(
            f"/api/jobs/{job_id}/metadata-status",
            json={"status": "completed", "message": "first pass"},
        )

        response = client_fixture.post(f"/api/jobs/{job_id}/reprocess-metadata")
        assert response.status_code == 200

        cursor.execute("SELECT metadata_status, metadata_message FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        assert row["metadata_status"] == "pending"
        assert row["metadata_message"] is None

        # Download state is untouched — re-drive only re-runs the extract pass.
        cursor.execute("SELECT status FROM chunks WHERE job_id = ?", (job_id,))
        assert cursor.fetchone()["status"] == ChunkStatus.DOWNLOADED.value

        redriven_task = client_fixture.get("/api/tasks/next").json()
        assert redriven_task["type"] == "extract"
        assert redriven_task["id"] == job_id

    def test_job_status_stays_in_progress_when_some_chunks_fail_while_others_are_still_active(
        self, client_fixture, db_connection_fixture
    ):
        job_data = {
            "job_id": "test-job-partial-failure",
            "user_id": "test-user-partial",
            "timestamp": "20240105T000000",
            "auth_user": "0",
            "cookie": "test-cookie-partial",
            "total_chunks": 3,
        }
        client_fixture.post("/api/jobs", json=job_data)

        conn = db_connection_fixture
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE job_id = ?", ("test-job-partial-failure",))
        job_id = cursor.fetchone()["id"]

        # Chunk 1 fails while chunks 2 and 3 are still pending (active work remains).
        task1 = client_fixture.get("/api/tasks/next").json()
        client_fixture.post(
            f"/api/tasks/{task1['id']}/status",
            json={"status": ChunkStatus.FAILED.value, "message": "curl error"},
        )

        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        assert cursor.fetchone()["status"] == JobStatus.IN_PROGRESS.value

        # Once every chunk has reached a terminal state and at least one failed,
        # the job is genuinely done and failed.
        task2 = client_fixture.get("/api/tasks/next").json()
        client_fixture.post(
            f"/api/tasks/{task2['id']}/status",
            json={"status": ChunkStatus.FAILED.value, "message": "curl error"},
        )
        task3 = client_fixture.get("/api/tasks/next").json()
        client_fixture.post(
            f"/api/tasks/{task3['id']}/status",
            json={"status": ChunkStatus.FAILED.value, "message": "curl error"},
        )

        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        assert cursor.fetchone()["status"] == JobStatus.FAILED.value

    def test_job_progress_aggregates_across_chunks(self, client_fixture, db_connection_fixture):
        job_data = {
            "job_id": "test-job-progress",
            "user_id": "test-user-progress",
            "timestamp": "20240106T000000",
            "auth_user": "0",
            "cookie": "test-cookie-progress",
            "total_chunks": 2,
        }
        client_fixture.post("/api/jobs", json=job_data)

        # Chunk 1 is claimed (now "downloading") and reports progress.
        task1 = client_fixture.get("/api/tasks/next").json()
        progress_response = client_fixture.post(
            f"/api/tasks/{task1['id']}/progress",
            json={"downloaded_bytes": 1000, "total_bytes": 5000, "speed_bytes_per_sec": 200.0},
        )
        assert progress_response.status_code == 200

        # Chunk 2 is claimed but hasn't reported progress yet (total_bytes unknown).
        client_fixture.get("/api/tasks/next")

        jobs = client_fixture.get("/api/jobs").json()
        job = next(j for j in jobs if j["job_id"] == "test-job-progress")

        assert job["total_downloaded_bytes"] == 1000
        assert job["total_expected_bytes"] == 5000
        assert job["combined_speed_bytes_per_sec"] == 200.0
        assert job["estimated_seconds_remaining"] == pytest.approx((5000 - 1000) / 200.0)

    def test_job_progress_excludes_speed_of_chunks_no_longer_downloading(
        self, client_fixture, db_connection_fixture
    ):
        job_data = {
            "job_id": "test-job-progress-done",
            "user_id": "test-user-progress-done",
            "timestamp": "20240107T000000",
            "auth_user": "0",
            "cookie": "test-cookie-progress-done",
            "total_chunks": 1,
        }
        client_fixture.post("/api/jobs", json=job_data)

        task1 = client_fixture.get("/api/tasks/next").json()
        client_fixture.post(
            f"/api/tasks/{task1['id']}/progress",
            json={"downloaded_bytes": 5000, "total_bytes": 5000, "speed_bytes_per_sec": 200.0},
        )
        client_fixture.post(
            f"/api/tasks/{task1['id']}/status",
            json={"status": ChunkStatus.DOWNLOADED.value, "message": "done"},
        )

        jobs = client_fixture.get("/api/jobs").json()
        job = next(j for j in jobs if j["job_id"] == "test-job-progress-done")

        # Bytes already downloaded still count, but a finished chunk isn't "active"
        # throughput anymore, so its stale speed shouldn't inflate the combined rate.
        assert job["total_downloaded_bytes"] == 5000
        assert job["combined_speed_bytes_per_sec"] == 0.0
        assert job["estimated_seconds_remaining"] is None

    def test_reextract_chunk_reruns_extraction_without_redownloading(
        self, client_fixture, db_connection_fixture
    ):
        """Re-extraction re-runs the whole-export GPTH pass; the worker is never asked
        to re-download, since the .tgz archives are retained on disk."""
        job_data = {
            "job_id": "test-job-reextract",
            "user_id": "test-user-reextract",
            "timestamp": "20240108T000000",
            "auth_user": "0",
            "cookie": "test-cookie-reextract",
            "total_chunks": 1,
        }
        client_fixture.post("/api/jobs", json=job_data)
        conn = db_connection_fixture
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE job_id = ?", ("test-job-reextract",))
        job_id = cursor.fetchone()["id"]

        task = client_fixture.get("/api/tasks/next").json()
        chunk_id = task["id"]
        client_fixture.post(
            f"/api/tasks/{chunk_id}/status",
            json={"status": ChunkStatus.DOWNLOADED.value, "message": "done"},
        )
        # Complete the initial extract pass.
        client_fixture.get("/api/tasks/next")
        client_fixture.post(
            f"/api/jobs/{job_id}/metadata-status",
            json={"status": "completed", "message": "first pass"},
        )

        response = client_fixture.post(f"/api/chunks/{chunk_id}/reextract")
        assert response.status_code == 200
        assert response.json()["message"] == "Chunk queued for re-extraction"

        cursor.execute("SELECT status, message FROM chunks WHERE id = ?", (chunk_id,))
        chunk = cursor.fetchone()
        assert chunk["status"] == ChunkStatus.DOWNLOADED.value
        assert chunk["message"] is None

        next_task = client_fixture.get("/api/tasks/next").json()
        assert next_task["type"] == "extract"
        assert next_task["id"] == job_id

    def test_reextract_nonexistent_chunk_returns_404(self, client_fixture, db_connection_fixture):
        response = client_fixture.post("/api/chunks/9999/reextract")
        assert response.status_code == 404

    def test_update_job_cookie(self, client_fixture, db_connection_fixture):
        job_data = {
            "job_id": "test-job-cookie-update",
            "user_id": "test-user-cookie",
            "timestamp": "20240105T000000",
            "auth_user": "0",
            "cookie": "old-cookie",
            "total_chunks": 1
        }
        client_fixture.post("/api/jobs", json=job_data)

        conn = db_connection_fixture
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE job_id = ?", ("test-job-cookie-update",))
        job = cursor.fetchone()
        assert job is not None
        job_id = job["id"]

        new_cookie_data = {"cookie": "new-cookie"}
        response = client_fixture.post(f"/api/jobs/{job_id}/cookie", json=new_cookie_data)
        assert response.status_code == 200
        assert response.json()["message"] == "Cookie updated successfully"

        cursor.execute("SELECT cookie FROM jobs WHERE id = ?", (job_id,))
        updated_job = cursor.fetchone()
        assert updated_job is not None
        assert updated_job["cookie"] == "new-cookie"

    def test_download_without_auto_extract_completes_at_downloaded_without_extraction(
        self, client_fixture, db_connection_fixture
    ):
        client_fixture.post("/api/jobs", json={
            "job_id": "job-no-extract", "user_id": "u", "timestamp": "20240201T000000",
            "auth_user": "0", "cookie": "c", "total_chunks": 1, "auto_extract": False,
        })
        conn = db_connection_fixture
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE job_id = ?", ("job-no-extract",))
        job_id = cursor.fetchone()["id"]

        task = client_fixture.get("/api/tasks/next").json()
        assert task["type"] == "download"
        client_fixture.post(
            f"/api/tasks/{task['id']}/status",
            json={"status": ChunkStatus.DOWNLOADED.value, "message": "done"},
        )

        # With auto-extract off, a downloaded chunk is terminal: no extract or
        # metadata task is offered, and the job is complete.
        assert client_fixture.get("/api/tasks/next").json() == {"task": "none"}
        cursor.execute("SELECT status, metadata_status FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        assert row["status"] == JobStatus.COMPLETED.value
        assert row["metadata_status"] is None

    def test_extract_pass_runs_after_downloads_and_completes_the_job(
        self, client_fixture, db_connection_fixture
    ):
        client_fixture.post("/api/jobs", json={
            "job_id": "job-gpth", "user_id": "u", "timestamp": "20240301T000000",
            "auth_user": "0", "cookie": "c", "total_chunks": 2,
        })
        conn = db_connection_fixture
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE job_id = ?", ("job-gpth",))
        job_id = cursor.fetchone()["id"]

        # Download both chunks — no per-chunk extract task is ever offered.
        for _ in range(2):
            task = client_fixture.get("/api/tasks/next").json()
            assert task["type"] == "download"
            client_fixture.post(
                f"/api/tasks/{task['id']}/status",
                json={"status": ChunkStatus.DOWNLOADED.value, "message": "done"},
            )

        # A single job-level GPTH extract pass is offered once downloads finish.
        extract_task = client_fixture.get("/api/tasks/next").json()
        assert extract_task["type"] == "extract"
        assert extract_task["id"] == job_id
        assert extract_task["params"]["total_chunks"] == 2
        assert extract_task["params"]["timestamp"] == "20240301T000000"

        # Job stays in progress until the extract pass reports back.
        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        assert cursor.fetchone()["status"] == JobStatus.IN_PROGRESS.value

        client_fixture.post(
            f"/api/jobs/{job_id}/metadata-status",
            json={"status": "completed", "message": "Extracted 100 files"},
        )
        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        assert cursor.fetchone()["status"] == JobStatus.COMPLETED.value


class TestArchivesAPI:
    @pytest.fixture
    def container_fixture(self):
        return ManagerContainer()

    @pytest.fixture
    def archives_dir(self, tmp_path, monkeypatch):
        d = tmp_path / "archives"
        d.mkdir()
        monkeypatch.setenv("APP_ARCHIVES_DIR", str(d))
        return d

    @pytest.fixture
    def db_connection_fixture(self, container_fixture, tmp_path):
        db_file = tmp_path / "test.db"
        db = Database(url=f"sqlite:///{db_file}")
        with container_fixture.database.override(db):
            conn = sqlite3.connect(str(db_file))
            conn.row_factory = sqlite3.Row
            yield conn
            conn.close()

    @pytest.fixture
    def client_fixture(self, container_fixture, db_connection_fixture, archives_dir):
        app = create_app(container_fixture)
        with TestClient(app) as c:
            yield c

    def _extract_single_chunk_job(self, client, timestamp):
        client.post("/api/jobs", json={
            "job_id": f"job-{timestamp}", "user_id": "u", "timestamp": timestamp,
            "auth_user": "0", "cookie": "c", "total_chunks": 1,
        })
        task = client.get("/api/tasks/next").json()
        client.post(f"/api/tasks/{task['id']}/status",
                    json={"status": ChunkStatus.DOWNLOADED.value, "message": "done"})
        task = client.get("/api/tasks/next").json()
        client.post(f"/api/tasks/{task['id']}/status",
                    json={"status": ChunkStatus.EXTRACTED.value, "message": "done"})

    def test_archives_lists_disk_files_reconciled_with_db(self, client_fixture, archives_dir):
        # One archive the app tracks (chunk extracted) and one orphan only on disk.
        self._extract_single_chunk_job(client_fixture, "20240101T000000")
        (archives_dir / "takeout-20240101T000000Z-1-001.tgz").write_bytes(b"x" * 10)
        (archives_dir / "takeout-Z-001.tgz").write_bytes(b"y" * 20)

        response = client_fixture.get("/api/archives")
        assert response.status_code == 200, response.text

        archives = {a["filename"]: a for a in response.json()}
        assert set(archives) == {
            "takeout-20240101T000000Z-1-001.tgz",
            "takeout-Z-001.tgz",
        }

        tracked = archives["takeout-20240101T000000Z-1-001.tgz"]
        assert tracked["size_bytes"] == 10
        assert tracked["export_timestamp"] == "2024-01-01T00:00:00Z"
        assert tracked["source"] == "db"
        assert tracked["extract_status"] == ChunkStatus.EXTRACTED.value

        orphan = archives["takeout-Z-001.tgz"]
        assert orphan["size_bytes"] == 20
        assert orphan["source"] == "disk"
        assert orphan["extract_status"] == "unknown"
        assert orphan["export_timestamp"] is None

    def test_extracting_an_orphan_archive_queues_an_extract_task_by_filename(
        self, client_fixture, archives_dir
    ):
        (archives_dir / "takeout-Z-001.tgz").write_bytes(b"data")

        response = client_fixture.post("/api/archives/takeout-Z-001.tgz/extract")
        assert response.status_code == 200, response.text

        task = client_fixture.get("/api/tasks/next").json()
        assert task["type"] == "extract_archive"
        assert task["params"]["filename"] == "takeout-Z-001.tgz"

    def test_extracting_a_missing_archive_returns_404(self, client_fixture, archives_dir):
        response = client_fixture.post("/api/archives/does-not-exist.tgz/extract")
        assert response.status_code == 404

    def test_deleting_an_archive_removes_it_from_disk(self, client_fixture, archives_dir):
        (archives_dir / "takeout-Z-001.tgz").write_bytes(b"data")

        response = client_fixture.delete("/api/archives/takeout-Z-001.tgz")
        assert response.status_code == 200
        assert not (archives_dir / "takeout-Z-001.tgz").exists()

        names = [a["filename"] for a in client_fixture.get("/api/archives").json()]
        assert "takeout-Z-001.tgz" not in names

    def test_deleting_a_missing_archive_returns_404(self, client_fixture, archives_dir):
        assert client_fixture.delete("/api/archives/nope.tgz").status_code == 404

    def test_requesting_a_timeline_queues_a_task_and_caches_the_result(
        self, client_fixture, archives_dir
    ):
        (archives_dir / "takeout-Z-001.tgz").write_bytes(b"data")

        assert client_fixture.post("/api/archives/takeout-Z-001.tgz/timeline").status_code == 200

        task = client_fixture.get("/api/tasks/next").json()
        assert task["type"] == "timeline"
        assert task["params"]["filename"] == "takeout-Z-001.tgz"

        # Before the worker reports, the timeline is in flight.
        pending = client_fixture.get("/api/archives/takeout-Z-001.tgz/timeline").json()
        assert pending["status"] == "processing"

        # The worker reports the month histogram keyed by filename (also the
        # piggyback path, which has no prior request row).
        client_fixture.post(
            "/api/archives/takeout-Z-001.tgz/timeline-result",
            json={"months": {"2019-07": 10, "2020-01": 5}},
        )

        done = client_fixture.get("/api/archives/takeout-Z-001.tgz/timeline").json()
        assert done["status"] == "completed"
        assert done["months"] == {"2019-07": 10, "2020-01": 5}

    def test_timelines_endpoint_lists_all_cached_timelines(self, client_fixture, archives_dir):
        (archives_dir / "takeout-Z-001.tgz").write_bytes(b"x")
        client_fixture.post(
            "/api/archives/takeout-Z-001.tgz/timeline-result",
            json={"months": {"2019-07": 3}},
        )

        listing = client_fixture.get("/api/timelines").json()
        entry = next(t for t in listing if t["filename"] == "takeout-Z-001.tgz")
        assert entry["status"] == "completed"
        assert entry["months"] == {"2019-07": 3}

    def test_reporting_archive_extraction_status_updates_the_record(
        self, client_fixture, archives_dir, db_connection_fixture
    ):
        (archives_dir / "takeout-Z-001.tgz").write_bytes(b"data")
        client_fixture.post("/api/archives/takeout-Z-001.tgz/extract")
        extraction_id = client_fixture.get("/api/tasks/next").json()["id"]

        response = client_fixture.post(
            f"/api/archive-extractions/{extraction_id}/status",
            json={"status": "extracted", "message": "Extracted 3 pictures and 1 videos"},
        )
        assert response.status_code == 200

        cursor = db_connection_fixture.cursor()
        cursor.execute(
            "SELECT status, message FROM archive_extractions WHERE id = ?", (extraction_id,)
        )
        row = cursor.fetchone()
        assert row["status"] == "extracted"
        assert row["message"] == "Extracted 3 pictures and 1 videos"
