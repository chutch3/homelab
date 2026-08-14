from __future__ import annotations

import pytest

from backend.db.database import Database
from backend.repositories import JobRepository
from backend.domain.models import JobRecord, MetadataTaskInfo
from backend.models import JobStatus, MetadataStatus


class TestJobRepository:
    @pytest.fixture()
    def subject(self) -> JobRepository:
        db = Database("sqlite:///:memory:")
        return JobRepository(session_factory=db.session)

    def test_create_returns_id(self, subject: JobRepository) -> None:
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

    def test_get_by_id_returns_created_job(self, subject: JobRepository) -> None:
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
        assert isinstance(result, JobRecord)
        assert result.id == row_id
        assert result.job_id == "test-job"
        assert result.user_id == "user-123"
        assert result.timestamp == "20240101T120000"
        assert result.auth_user == "0"
        assert result.cookie == "test-cookie"
        assert result.total_chunks == 3
        assert result.status == JobStatus.PENDING.value

    def test_get_by_id_returns_none_for_missing(self, subject: JobRepository) -> None:
        result = subject.get_by_id(9999)

        assert result is None

    def test_list_all_returns_all_jobs(self, subject: JobRepository) -> None:
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
        assert all(isinstance(r, JobRecord) for r in result)
        job_ids = [r.job_id for r in result]
        assert "job-1" in job_ids
        assert "job-2" in job_ids

    def test_update_status(self, subject: JobRepository) -> None:
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )

        subject.update_status(row_id, JobStatus.COMPLETED)

        result = subject.get_by_id(row_id)
        assert result is not None
        assert result.status == JobStatus.COMPLETED.value

    def test_update_cookie(self, subject: JobRepository) -> None:
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="old-cookie", total_chunks=1,
        )

        subject.update_cookie(row_id, "new-cookie")

        result = subject.get_by_id(row_id)
        assert result is not None
        assert result.cookie == "new-cookie"

    def test_update_status_if_failed_updates_when_failed(self, subject: JobRepository) -> None:
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )
        subject.update_status(row_id, JobStatus.FAILED)

        subject.update_status_if_failed(row_id, JobStatus.IN_PROGRESS)

        result = subject.get_by_id(row_id)
        assert result is not None
        assert result.status == JobStatus.IN_PROGRESS.value

    def test_new_job_has_no_metadata_status(self, subject: JobRepository) -> None:
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )

        result = subject.get_by_id(row_id)

        assert result is not None
        assert result.metadata_status is None
        assert result.metadata_message is None

    def test_mark_metadata_pending(self, subject: JobRepository) -> None:
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )

        subject.mark_metadata_pending(row_id)

        result = subject.get_by_id(row_id)
        assert result is not None
        assert result.metadata_status == MetadataStatus.PENDING.value

    def test_mark_metadata_pending_overwrites_terminal_status(self, subject: JobRepository) -> None:
        """The manual re-drive path: reset even a completed/failed metadata run
        back to pending, without touching anything else about the job."""
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )
        subject.mark_metadata_pending(row_id)
        subject.update_metadata_status(row_id, MetadataStatus.COMPLETED, "done")

        subject.mark_metadata_pending(row_id)

        result = subject.get_by_id(row_id)
        assert result is not None
        assert result.metadata_status == MetadataStatus.PENDING.value

    def test_claim_next_pending_metadata_job(self, subject: JobRepository) -> None:
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=3,
        )
        subject.mark_metadata_pending(row_id)

        result = subject.claim_next_pending_metadata_job()

        assert result is not None
        assert isinstance(result, MetadataTaskInfo)
        assert result.id == row_id
        assert result.job_id == "test-job"
        assert result.timestamp == "20240101T000000"
        assert result.total_chunks == 3
        claimed = subject.get_by_id(row_id)
        assert claimed.metadata_status == MetadataStatus.PROCESSING.value

    def test_claim_next_pending_metadata_job_returns_none_when_empty(self, subject: JobRepository) -> None:
        assert subject.claim_next_pending_metadata_job() is None

    def test_claim_next_pending_metadata_job_ignores_jobs_never_marked_pending(
        self, subject: JobRepository
    ) -> None:
        subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )

        assert subject.claim_next_pending_metadata_job() is None

    def test_update_metadata_status(self, subject: JobRepository) -> None:
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )
        subject.mark_metadata_pending(row_id)

        subject.update_metadata_status(row_id, MetadataStatus.FAILED, "gpth crashed")

        result = subject.get_by_id(row_id)
        assert result is not None
        assert result.metadata_status == MetadataStatus.FAILED.value
        assert result.metadata_message == "gpth crashed"

    def test_update_status_if_failed_skips_non_failed(self, subject: JobRepository) -> None:
        row_id = subject.create(
            job_id="test-job", user_id="u1", timestamp="20240101T000000",
            auth_user="0", cookie="c", total_chunks=1,
        )
        subject.update_status(row_id, JobStatus.IN_PROGRESS)

        subject.update_status_if_failed(row_id, JobStatus.COMPLETED)

        result = subject.get_by_id(row_id)
        assert result is not None
        assert result.status == JobStatus.IN_PROGRESS.value
