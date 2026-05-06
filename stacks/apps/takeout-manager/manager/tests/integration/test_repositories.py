import pytest

from backend.db import Database
from backend.repositories import JobRepository, ChunkRepository
from backend.models import JobStatus, ChunkStatus


@pytest.fixture
def db(tmp_path):
    database = Database(db_path=str(tmp_path / "test.db"))
    database.ensure_path_exists()
    database.create_tables()
    return database


class TestJobRepository:
    @pytest.fixture
    def subject(self, db):
        return JobRepository(db)

    def test_create_returns_id(self, subject):
        job_id = subject.create(
            job_id="test-job",
            user_id="user-123",
            timestamp="20240101T120000",
            auth_user="0",
            cookie="test-cookie",
            total_chunks=5,
        )

        assert isinstance(job_id, int)
        assert job_id > 0

    def test_get_by_id_returns_created_job(self, subject):
        row_id = subject.create(
            job_id="test-job",
            user_id="user-123",
            timestamp="20240101T120000",
            auth_user="0",
            cookie="test-cookie",
            total_chunks=3,
        )

        result = subject.get_by_id(row_id)

        assert result is not None
        assert result["job_id"] == "test-job"
        assert result["user_id"] == "user-123"
        assert result["total_chunks"] == 3

    def test_get_by_id_returns_none_for_missing(self, subject):
        result = subject.get_by_id(9999)

        assert result is None

    def test_list_all_returns_all_jobs(self, subject):
        subject.create(
            job_id="job-1", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c1", total_chunks=1,
        )
        subject.create(
            job_id="job-2", user_id="u2", timestamp="20240102T000000",
            auth_user="0", cookie="c2", total_chunks=2,
        )

        result = subject.list_all()

        assert len(result) == 2
        job_ids = [r["job_id"] for r in result]
        assert "job-1" in job_ids
        assert "job-2" in job_ids

    def test_update_status(self, subject):
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )

        subject.update_status(row_id, JobStatus.COMPLETED)

        result = subject.get_by_id(row_id)
        assert result["status"] == JobStatus.COMPLETED.value

    def test_update_cookie(self, subject):
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="old-cookie", total_chunks=1,
        )

        subject.update_cookie(row_id, "new-cookie")

        result = subject.get_by_id(row_id)
        assert result["cookie"] == "new-cookie"

    def test_update_status_if_failed_updates_when_failed(self, subject):
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )
        subject.update_status(row_id, JobStatus.FAILED)

        subject.update_status_if_failed(row_id, JobStatus.IN_PROGRESS)

        result = subject.get_by_id(row_id)
        assert result["status"] == JobStatus.IN_PROGRESS.value

    def test_update_status_if_failed_skips_non_failed(self, subject):
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )
        subject.update_status(row_id, JobStatus.IN_PROGRESS)

        subject.update_status_if_failed(row_id, JobStatus.COMPLETED)

        result = subject.get_by_id(row_id)
        assert result["status"] == JobStatus.IN_PROGRESS.value


class TestChunkRepository:
    @pytest.fixture
    def job_repo(self, db):
        return JobRepository(db)

    @pytest.fixture
    def subject(self, db):
        return ChunkRepository(db)

    @pytest.fixture
    def job_id(self, job_repo):
        return job_repo.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=3,
        )

    def test_create_chunks_for_job(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=3)

        chunks = subject.list_for_job(job_id)
        assert len(chunks) == 3
        indices = sorted(c["chunk_index"] for c in chunks)
        assert indices == [1, 2, 3]

    def test_get_by_id_returns_chunk(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=2)
        chunks = subject.list_for_job(job_id)
        chunk_id = chunks[0]["id"]

        result = subject.get_by_id(chunk_id)

        assert result is not None
        assert result["id"] == chunk_id

    def test_get_next_pending_download_claims_chunk(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=2)

        result = subject.get_next_pending_download()

        assert result is not None
        claimed = subject.get_by_id(result["id"])
        assert claimed["status"] == ChunkStatus.DOWNLOADING.value

    def test_get_next_pending_download_returns_none_when_empty(self, subject):
        result = subject.get_next_pending_download()

        assert result is None

    def test_get_next_pending_download_skips_claimed_chunks(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=2)

        first = subject.get_next_pending_download()
        second = subject.get_next_pending_download()

        assert first is not None
        assert second is not None
        assert first["id"] != second["id"]

    def test_update_status(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=1)
        chunk = subject.get_next_pending_download()

        subject.update_status(chunk["id"], ChunkStatus.DOWNLOADED, "Download complete")

        updated = subject.get_by_id(chunk["id"])
        assert updated["status"] == ChunkStatus.DOWNLOADED.value
        assert updated["message"] == "Download complete"

    def test_get_job_id_for_chunk(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=1)
        chunk = subject.get_next_pending_download()

        result = subject.get_job_id_for_chunk(chunk["id"])

        assert result == job_id

    def test_get_job_id_for_chunk_returns_none_when_missing(self, subject):
        result = subject.get_job_id_for_chunk(9999)

        assert result is None

    def test_get_all_statuses_for_job(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=2)
        chunk1 = subject.get_next_pending_download()
        chunk2 = subject.get_next_pending_download()
        subject.update_status(chunk1["id"], ChunkStatus.DOWNLOADED, "done")
        subject.update_status(chunk2["id"], ChunkStatus.FAILED, "error")

        statuses = subject.get_all_statuses_for_job(job_id)

        assert sorted(statuses) == sorted([ChunkStatus.DOWNLOADED.value, ChunkStatus.FAILED.value])

    def test_get_failed_for_job(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=3)
        chunk1 = subject.get_next_pending_download()
        chunk2 = subject.get_next_pending_download()
        subject.update_status(chunk1["id"], ChunkStatus.FAILED, "error")
        subject.update_status(chunk2["id"], ChunkStatus.DOWNLOADED, "done")

        failed = subject.get_failed_for_job(job_id)

        assert len(failed) == 1
        assert failed[0]["id"] == chunk1["id"]

    def test_get_status_counts_for_job(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=3)
        chunk1 = subject.get_next_pending_download()
        chunk2 = subject.get_next_pending_download()
        subject.update_status(chunk1["id"], ChunkStatus.DOWNLOADED, "done")
        subject.update_status(chunk2["id"], ChunkStatus.EXTRACTED, "done")

        counts = subject.get_status_counts_for_job(job_id)

        assert counts.get(ChunkStatus.DOWNLOADED.value, 0) == 1
        assert counts.get(ChunkStatus.EXTRACTED.value, 0) == 1

    def test_list_for_job_returns_chunks(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=2)

        result = subject.list_for_job(job_id)

        assert len(result) == 2

    def test_reset_to_pending_download(self, subject, job_id):
        subject.create_chunks_for_job(job_id=job_id, total_chunks=1)
        chunk = subject.get_next_pending_download()
        subject.update_status(chunk["id"], ChunkStatus.DOWNLOADED, "done")

        subject.reset_to_pending_download(chunk["id"])

        reset = subject.get_by_id(chunk["id"])
        assert reset["status"] == ChunkStatus.PENDING_DOWNLOAD.value
        assert reset["message"] is None
