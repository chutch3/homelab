import pytest
from backend.containers import Database, ManagerContainer
from backend.application import create_app
from fastapi.testclient import TestClient
import sqlite3
from backend.models import JobStatus, ChunkStatus


@pytest.fixture(scope="function")
def container_fixture():
    return ManagerContainer()


@pytest.fixture(scope="function")
def db_connection_fixture(container_fixture, tmp_path):
    # This fixture sets up a clean database for each test function
    db_file = tmp_path / "test.db"

    # Override the database provider in the container for this test
    with container_fixture.database.override(Database(db_path=str(db_file))):
        db_instance = container_fixture.database()
        db_instance.ensure_path_exists()
        db_instance.create_tables()
        conn = db_instance.get_connection()
        try:
            yield conn # Provide the connection to the test
        finally:
            conn.close() # Ensure connection is closed after test

@pytest.fixture(scope="function")
def client_fixture(container_fixture, db_connection_fixture): # client_fixture now depends on db_connection_fixture
    # The container's database is already overridden by db_connection_fixture
    # and tables are created. We just need to create the app and TestClient.
    app = create_app(container_fixture)
    with TestClient(app) as c:
        yield c


class TestJobAPI:
    def test_create_job_and_get_next_task(self, client_fixture, db_connection_fixture):
        """
        Tests creating a job and then fetching the first chunk as a task.
        """
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
        """
        Tests that a worker can report task status and update the database.
        """
        # 1. Create a new job to get a chunk
        job_data = {
            "job_id": "test-job-update",
            "user_id": "test-user-update",
            "timestamp": "20240101T000000",
            "auth_user": "0",
            "cookie": "test-cookie-update",
            "total_chunks": 1
        }
        client_fixture.post("/api/jobs", json=job_data)

        # 2. Get the task details
        task_response = client_fixture.get("/api/tasks/next")
        task = task_response.json()
        task_id = task["id"]

        # 3. Report status as complete
        status_data = {"status": ChunkStatus.DOWNLOADED.value, "message": "Chunk downloaded successfully"}
        response = client_fixture.post(f"/api/tasks/{task_id}/status", json=status_data)
        assert response.status_code == 200
        assert response.json()["message"] == "Status received"

        # 4. Assert chunk status in database is updated
        # Use the connection from the fixture
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
        """
        Tests that the API returns 'none' when no tasks are available.
        """
        response = client_fixture.get("/api/tasks/next")
        assert response.status_code == 200
        assert response.json() == {"task": "none"}

    def test_job_status_updates_on_chunk_completion(self, client_fixture, db_connection_fixture):
        """
        Tests that the overall job status updates when chunks are completed.
        """
        # 1. Create a new job with multiple chunks
        job_data = {
            "job_id": "test-job-status-update",
            "user_id": "test-user-status",
            "timestamp": "20240102T000000",
            "auth_user": "0",
            "cookie": "test-cookie-status",
            "total_chunks": 2 # Two chunks for this job
        }
        client_fixture.post("/api/jobs", json=job_data)

        # Get the job_id (actual ID from DB)
        conn = db_connection_fixture
        cursor = conn.cursor()
        cursor.execute("SELECT id, status FROM jobs WHERE job_id = ?", ("test-job-status-update",))
        job = cursor.fetchone()
        assert job is not None
        assert job["status"] == JobStatus.PENDING.value
        job_id = job["id"]

        # 2. Get and complete the first chunk
        task1_response = client_fixture.get("/api/tasks/next")
        task1 = task1_response.json()
        assert task1["params"]["chunk_index"] == 1
        client_fixture.post(f"/api/tasks/{task1['id']}/status", json={"status": ChunkStatus.DOWNLOADED.value, "message": "Chunk 1 done"})

        # Job status should now be 'in_progress'
        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        job_status_after_first_chunk = cursor.fetchone()["status"]
        assert job_status_after_first_chunk == JobStatus.IN_PROGRESS.value

        # 3. Get and complete the second chunk
        task2_response = client_fixture.get("/api/tasks/next")
        task2 = task2_response.json()
        assert task2["params"]["chunk_index"] == 2
        client_fixture.post(f"/api/tasks/{task2['id']}/status", json={"status": ChunkStatus.DOWNLOADED.value, "message": "Chunk 2 done"})

        # Job status should still be 'in_progress' (not completed until extracted)
        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        job_status_after_all_chunks = cursor.fetchone()["status"]
        assert job_status_after_all_chunks == JobStatus.IN_PROGRESS.value


    def test_job_status_updates_to_completed_after_all_extracted(self, client_fixture, db_connection_fixture):
        """
        Tests that the overall job status updates to 'completed' only after all chunks are extracted.
        """
        # 1. Create a new job with two chunks
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

        # 2. Complete download for both chunks
        task1_dl_response = client_fixture.get("/api/tasks/next")
        task1_dl = task1_dl_response.json()
        client_fixture.post(f"/api/tasks/{task1_dl['id']}/status", json={"status": ChunkStatus.DOWNLOADED.value, "message": "Chunk 1 downloaded"})

        task2_dl_response = client_fixture.get("/api/tasks/next")
        task2_dl = task2_dl_response.json()
        client_fixture.post(f"/api/tasks/{task2_dl['id']}/status", json={"status": ChunkStatus.DOWNLOADED.value, "message": "Chunk 2 downloaded"})

        # Job status should be IN_PROGRESS (not COMPLETED yet)
        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        job_status_after_downloads = cursor.fetchone()["status"]
        assert job_status_after_downloads == JobStatus.IN_PROGRESS.value

        # 3. Get and complete extraction for first chunk
        task1_ext_response = client_fixture.get("/api/tasks/next")
        task1_ext = task1_ext_response.json()
        assert task1_ext["id"] == task1_dl["id"]
        client_fixture.post(f"/api/tasks/{task1_ext['id']}/status", json={"status": ChunkStatus.EXTRACTED.value, "message": "Chunk 1 extracted"})

        # Job status should still be IN_PROGRESS
        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        job_status_after_first_extract = cursor.fetchone()["status"]
        assert job_status_after_first_extract == JobStatus.IN_PROGRESS.value

        # 4. Get and complete extraction for second chunk
        task2_ext_response = client_fixture.get("/api/tasks/next")
        task2_ext = task2_ext_response.json()
        assert task2_ext["id"] == task2_dl["id"]
        client_fixture.post(f"/api/tasks/{task2_ext['id']}/status", json={"status": ChunkStatus.EXTRACTED.value, "message": "Chunk 2 extracted"})

        # Now job status should be COMPLETED
        cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        job_status_final = cursor.fetchone()["status"]
        assert job_status_final == JobStatus.COMPLETED.value

    def test_update_job_cookie(self, client_fixture, db_connection_fixture):
        """
        Tests that the cookie for a job can be updated.
        """
        # 1. Create a job
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

        # 2. Update the cookie
        new_cookie_data = {"cookie": "new-cookie"}
        response = client_fixture.post(f"/api/jobs/{job_id}/cookie", json=new_cookie_data)
        assert response.status_code == 200
        assert response.json()["message"] == "Cookie updated successfully"

        # 3. Verify the cookie was updated in the database
        cursor.execute("SELECT cookie FROM jobs WHERE id = ?", (job_id,))
        updated_job = cursor.fetchone()
        assert updated_job is not None
        assert updated_job["cookie"] == "new-cookie"
