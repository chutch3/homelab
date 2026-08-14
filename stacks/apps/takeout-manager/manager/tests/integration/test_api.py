import pytest
from backend.containers import ManagerContainer
from backend.db import Database
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
        with container_fixture.database.override(Database(db_path=str(db_file))):
            conn = container_fixture.database().get_connection()
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

    def test_update_task_status_completes_chunk(self, client_fixture, container_fixture):
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

        db = container_fixture.database()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, message FROM chunks WHERE id = ?", (task_id,))
        updated_chunk = cursor.fetchone()
        conn.close()

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

    def test_job_status_updates_to_completed_after_all_extracted(self, client_fixture, db_connection_fixture):
        job_data = {
            "job_id": "test-job-complete-extract",
            "user_id": "test-user-complete",
            "timestamp": "20240104T000000",
            "auth_user": "0",
            "cookie": "test-cookie-complete",
            "total_chunks": 2
        }
        client_fixture.post("/api/jobs", json=job_data)

        conn = db_connection_fixture
        cursor = conn.cursor()
        cursor.execute("SELECT id, status FROM jobs WHERE job_id = ?", ("test-job-complete-extract",))
        job = cursor.fetchone()
        assert job is not None
        assert job["status"] == JobStatus.PENDING.value
        job_id = job["id"]

        task1_dl_response = client_fixture.get("/api/tasks/next")
        task1_dl = task1_dl_response.json()
        client_fixture.post(f"/api/tasks/{task1_dl['id']}/status", json={"status": ChunkStatus.DOWNLOADED.value, "message": "Chunk 1 downloaded"})

        task2_dl_response = client_fixture.get("/api/tasks/next")
        task2_dl = task2_dl_response.json()
        client_fixture.post(f"/api/tasks/{task2_dl['id']}/status", json={"status": ChunkStatus.DOWNLOADED.value, "message": "Chunk 2 downloaded"})

        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        job_status_after_downloads = cursor.fetchone()["status"]
        assert job_status_after_downloads == JobStatus.IN_PROGRESS.value

        task1_ext_response = client_fixture.get("/api/tasks/next")
        task1_ext = task1_ext_response.json()
        assert task1_ext["id"] == task1_dl["id"]
        client_fixture.post(f"/api/tasks/{task1_ext['id']}/status", json={"status": ChunkStatus.EXTRACTED.value, "message": "Chunk 1 extracted"})

        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        job_status_after_first_extract = cursor.fetchone()["status"]
        assert job_status_after_first_extract == JobStatus.IN_PROGRESS.value

        task2_ext_response = client_fixture.get("/api/tasks/next")
        task2_ext = task2_ext_response.json()
        assert task2_ext["id"] == task2_dl["id"]
        client_fixture.post(f"/api/tasks/{task2_ext['id']}/status", json={"status": ChunkStatus.EXTRACTED.value, "message": "Chunk 2 extracted"})

        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        job_status_final = cursor.fetchone()["status"]
        assert job_status_final == JobStatus.COMPLETED.value

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
