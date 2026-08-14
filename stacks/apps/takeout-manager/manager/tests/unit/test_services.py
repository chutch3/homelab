import pytest
from unittest.mock import Mock

from backend.services import JobService, ChunkService, TaskService
from backend.models import JobStatus, ChunkStatus, TakeoutJob
from backend.repositories import JobRepository, ChunkRepository
from backend.domain.models import ChunkRecord, DownloadTaskInfo, ExtractTaskInfo, JobRecord


def _job_record(**overrides):
    defaults = dict(
        id=1, job_id="job-1", timestamp="20240101T120000", total_chunks=1,
        status=JobStatus.PENDING.value, cookie="cookie", user_id="user-1", auth_user="0",
    )
    defaults.update(overrides)
    return JobRecord(**defaults)


def _chunk_record(**overrides):
    defaults = dict(
        id=1, job_id=1, chunk_index=1, status=ChunkStatus.PENDING_DOWNLOAD.value,
        message=None, downloaded_bytes=0, total_bytes=None, speed_bytes_per_sec=None,
    )
    defaults.update(overrides)
    return ChunkRecord(**defaults)


class TestJobService:
    @pytest.fixture
    def mock_job_repo(self):
        return Mock(spec=JobRepository)

    @pytest.fixture
    def mock_chunk_repo(self):
        return Mock(spec=ChunkRepository)

    @pytest.fixture
    def subject(self, mock_job_repo, mock_chunk_repo):
        return JobService(mock_job_repo, mock_chunk_repo)

    def test_create_job(self, subject, mock_job_repo, mock_chunk_repo):
        mock_job_repo.create.return_value = 123
        job = TakeoutJob(
            job_id="test-job",
            user_id="user-1",
            timestamp="20240101T120000",
            auth_user="0",
            cookie="test-cookie",
            total_chunks=5,
        )

        result = subject.create_job(job)

        assert "message" in result
        assert result["job_id"] == 123
        assert "5 chunks" in result["message"]
        mock_job_repo.create.assert_called_once()
        mock_chunk_repo.create_chunks_for_job.assert_called_once_with(123, 5)

    def test_list_jobs(self, subject, mock_job_repo, mock_chunk_repo):
        mock_job_repo.list_all.return_value = [
            _job_record(id=1, job_id="job-1", user_id="user-1", timestamp="20240101T120000",
                        total_chunks=5, status=JobStatus.IN_PROGRESS.value)
        ]
        mock_chunk_repo.get_status_counts_for_job.return_value = {
            ChunkStatus.EXTRACTED.value: 2,
            ChunkStatus.DOWNLOADED.value: 1,
            ChunkStatus.FAILED.value: 1,
        }
        mock_chunk_repo.get_progress_for_job.return_value = []

        result = subject.list_jobs()

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["extracted_chunks"] == 2
        assert result[0]["failed_chunks"] == 1
        assert result[0]["progress"] == 40

    def test_list_jobs_includes_byte_progress_aggregate(self, subject, mock_job_repo, mock_chunk_repo):
        mock_job_repo.list_all.return_value = [
            _job_record(id=1, job_id="job-1", user_id="user-1", timestamp="20240101T120000",
                        total_chunks=2, status=JobStatus.IN_PROGRESS.value)
        ]
        mock_chunk_repo.get_status_counts_for_job.return_value = {}
        mock_chunk_repo.get_progress_for_job.return_value = [
            _chunk_record(id=1, status=ChunkStatus.DOWNLOADING.value,
                          downloaded_bytes=1000, total_bytes=5000, speed_bytes_per_sec=200.0),
            _chunk_record(id=2, status=ChunkStatus.PENDING_DOWNLOAD.value,
                          downloaded_bytes=0, total_bytes=None, speed_bytes_per_sec=None),
        ]

        result = subject.list_jobs()

        assert result[0]["total_downloaded_bytes"] == 1000
        assert result[0]["total_expected_bytes"] == 5000
        assert result[0]["combined_speed_bytes_per_sec"] == 200.0
        assert result[0]["estimated_seconds_remaining"] == pytest.approx(20.0)

    def test_update_cookie_success(self, subject, mock_job_repo):
        mock_job_repo.get_by_id.return_value = _job_record(id=1, job_id="test-job")

        subject.update_cookie(1, "new-cookie")

        mock_job_repo.update_cookie.assert_called_once_with(1, "new-cookie")

    def test_update_cookie_not_found(self, subject, mock_job_repo):
        mock_job_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Job 1 not found"):
            subject.update_cookie(1, "new-cookie")

    def test_retry_failed_chunks(self, subject, mock_job_repo, mock_chunk_repo):
        mock_job_repo.get_by_id.return_value = _job_record(id=1)
        mock_chunk_repo.get_failed_for_job.return_value = [
            _chunk_record(id=10, chunk_index=1, status=ChunkStatus.FAILED.value),
            _chunk_record(id=11, chunk_index=2, status=ChunkStatus.FAILED.value),
        ]

        result = subject.retry_failed_chunks(1)

        assert result["retried_count"] == 2
        assert mock_chunk_repo.reset_to_pending_download.call_count == 2
        mock_job_repo.update_status_if_failed.assert_called_once_with(1, JobStatus.IN_PROGRESS)

    def test_retry_failed_chunks_none_failed(self, subject, mock_job_repo, mock_chunk_repo):
        mock_job_repo.get_by_id.return_value = _job_record(id=1)
        mock_chunk_repo.get_failed_for_job.return_value = []

        result = subject.retry_failed_chunks(1)

        assert result["retried_count"] == 0
        mock_chunk_repo.reset_to_pending_download.assert_not_called()


class TestCalculateJobProgress:
    @pytest.fixture
    def subject(self):
        return JobService(Mock(spec=JobRepository), Mock(spec=ChunkRepository))

    def test_returns_zero_defaults_when_no_chunks_have_reported(self, subject):
        chunks = [
            _chunk_record(status=ChunkStatus.PENDING_DOWNLOAD.value,
                          downloaded_bytes=0, total_bytes=None, speed_bytes_per_sec=None),
        ]

        result = subject._calculate_job_progress(chunks)

        assert result == {
            "total_downloaded_bytes": 0,
            "total_expected_bytes": 0,
            "combined_speed_bytes_per_sec": 0.0,
            "estimated_seconds_remaining": None,
        }

    def test_sums_downloaded_and_expected_bytes_across_active_chunks(self, subject):
        chunks = [
            _chunk_record(status=ChunkStatus.DOWNLOADING.value,
                          downloaded_bytes=1000, total_bytes=5000, speed_bytes_per_sec=200.0),
            _chunk_record(status=ChunkStatus.DOWNLOADING.value,
                          downloaded_bytes=2000, total_bytes=4000, speed_bytes_per_sec=100.0),
        ]

        result = subject._calculate_job_progress(chunks)

        assert result["total_downloaded_bytes"] == 3000
        assert result["total_expected_bytes"] == 9000
        assert result["combined_speed_bytes_per_sec"] == 300.0
        assert result["estimated_seconds_remaining"] == pytest.approx((9000 - 3000) / 300.0)

    def test_excludes_speed_of_chunks_no_longer_downloading(self, subject):
        chunks = [
            _chunk_record(status=ChunkStatus.DOWNLOADED.value,
                          downloaded_bytes=5000, total_bytes=5000, speed_bytes_per_sec=200.0),
        ]

        result = subject._calculate_job_progress(chunks)

        assert result["total_downloaded_bytes"] == 5000
        assert result["combined_speed_bytes_per_sec"] == 0.0
        assert result["estimated_seconds_remaining"] is None

    def test_estimated_seconds_remaining_is_none_when_speed_is_zero(self, subject):
        chunks = [
            _chunk_record(status=ChunkStatus.DOWNLOADING.value,
                          downloaded_bytes=1000, total_bytes=5000, speed_bytes_per_sec=0.0),
        ]

        result = subject._calculate_job_progress(chunks)

        assert result["estimated_seconds_remaining"] is None


class TestChunkService:
    @pytest.fixture
    def mock_job_repo(self):
        return Mock(spec=JobRepository)

    @pytest.fixture
    def mock_chunk_repo(self):
        return Mock(spec=ChunkRepository)

    @pytest.fixture
    def subject(self, mock_job_repo, mock_chunk_repo):
        return ChunkService(mock_job_repo, mock_chunk_repo)

    def test_get_chunks_for_job(self, subject, mock_job_repo, mock_chunk_repo):
        mock_job_repo.get_by_id.return_value = _job_record(id=1)
        mock_chunk_repo.list_for_job.return_value = [
            _chunk_record(id=1, chunk_index=1, status=ChunkStatus.DOWNLOADED.value),
            _chunk_record(id=2, chunk_index=2, status=ChunkStatus.EXTRACTED.value),
        ]

        result = subject.get_chunks_for_job(1)

        assert len(result) == 2
        mock_chunk_repo.list_for_job.assert_called_once_with(1)

    def test_get_chunks_for_nonexistent_job(self, subject, mock_job_repo):
        mock_job_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Job 1 not found"):
            subject.get_chunks_for_job(1)

    def test_retry_chunk(self, subject, mock_job_repo, mock_chunk_repo):
        mock_chunk_repo.get_by_id.return_value = _chunk_record(id=10, job_id=1)

        subject.retry_chunk(10)

        mock_chunk_repo.reset_to_pending_download.assert_called_once_with(10)
        mock_job_repo.update_status_if_failed.assert_called_once_with(1, JobStatus.IN_PROGRESS)

    def test_retry_nonexistent_chunk(self, subject, mock_chunk_repo):
        mock_chunk_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Chunk 10 not found"):
            subject.retry_chunk(10)

    def test_update_progress(self, subject, mock_chunk_repo):
        subject.update_progress(10, downloaded_bytes=1000, total_bytes=5000, speed_bytes_per_sec=200.0)

        mock_chunk_repo.update_progress.assert_called_once_with(10, 1000, 5000, 200.0)

    def test_reextract_chunk(self, subject, mock_job_repo, mock_chunk_repo):
        mock_chunk_repo.get_by_id.return_value = _chunk_record(id=10, job_id=1)

        subject.reextract_chunk(10)

        mock_chunk_repo.reset_to_downloaded.assert_called_once_with(10)
        mock_job_repo.update_status_if_failed.assert_called_once_with(1, JobStatus.IN_PROGRESS)

    def test_reextract_nonexistent_chunk(self, subject, mock_chunk_repo):
        mock_chunk_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Chunk 10 not found"):
            subject.reextract_chunk(10)


class TestTaskService:
    @pytest.fixture
    def mock_job_repo(self):
        return Mock(spec=JobRepository)

    @pytest.fixture
    def mock_chunk_repo(self):
        return Mock(spec=ChunkRepository)

    @pytest.fixture
    def subject(self, mock_job_repo, mock_chunk_repo):
        return TaskService(mock_job_repo, mock_chunk_repo)

    def test_get_next_task_download(self, subject, mock_chunk_repo):
        mock_chunk_repo.get_next_pending_download.return_value = DownloadTaskInfo(
            id=1, job_id="test-job", user_id="user-1", timestamp="20240101T120000",
            auth_user="0", cookie="test-cookie", chunk_index=1,
        )

        result = subject.get_next_task()

        assert result["type"] == "download"
        assert result["id"] == 1
        assert result["params"]["chunk_index"] == 1

    def test_get_next_task_extract(self, subject, mock_chunk_repo):
        mock_chunk_repo.get_next_pending_download.return_value = None
        mock_chunk_repo.get_next_downloaded.return_value = ExtractTaskInfo(
            id=2, job_id="test-job", chunk_index=1, timestamp="20240101T120000",
        )

        result = subject.get_next_task()

        assert result["type"] == "extract"
        assert result["id"] == 2

    def test_get_next_task_none_available(self, subject, mock_chunk_repo):
        mock_chunk_repo.get_next_pending_download.return_value = None
        mock_chunk_repo.get_next_downloaded.return_value = None

        result = subject.get_next_task()

        assert result == {"task": "none"}

    def test_update_task_status_completed(self, subject, mock_job_repo, mock_chunk_repo):
        mock_chunk_repo.get_job_id_for_chunk.return_value = 1
        mock_chunk_repo.get_all_statuses_for_job.return_value = [
            ChunkStatus.EXTRACTED.value,
            ChunkStatus.EXTRACTED.value,
        ]

        subject.update_task_status(10, ChunkStatus.EXTRACTED, "Done")

        mock_chunk_repo.update_status.assert_called_once_with(10, ChunkStatus.EXTRACTED, "Done")
        mock_job_repo.update_status.assert_called_once_with(1, JobStatus.COMPLETED)

    def test_update_task_status_failed(self, subject, mock_job_repo, mock_chunk_repo):
        mock_chunk_repo.get_job_id_for_chunk.return_value = 1
        mock_chunk_repo.get_all_statuses_for_job.return_value = [
            ChunkStatus.EXTRACTED.value,
            ChunkStatus.FAILED.value,
        ]

        subject.update_task_status(10, ChunkStatus.FAILED, "curl error")

        mock_job_repo.update_status.assert_called_once_with(1, JobStatus.FAILED)

    def test_update_task_status_stays_in_progress_when_other_chunks_still_active(
        self, subject, mock_job_repo, mock_chunk_repo
    ):
        mock_chunk_repo.get_job_id_for_chunk.return_value = 1
        mock_chunk_repo.get_all_statuses_for_job.return_value = [
            ChunkStatus.FAILED.value,
            ChunkStatus.DOWNLOADING.value,
            ChunkStatus.PENDING_DOWNLOAD.value,
        ]

        subject.update_task_status(10, ChunkStatus.FAILED, "curl error")

        mock_job_repo.update_status.assert_called_once_with(1, JobStatus.IN_PROGRESS)

    def test_update_task_status_in_progress(self, subject, mock_job_repo, mock_chunk_repo):
        mock_chunk_repo.get_job_id_for_chunk.return_value = 1
        mock_chunk_repo.get_all_statuses_for_job.return_value = [
            ChunkStatus.DOWNLOADED.value,
            ChunkStatus.EXTRACTED.value,
        ]

        subject.update_task_status(10, ChunkStatus.DOWNLOADED, "done")

        mock_job_repo.update_status.assert_called_once_with(1, JobStatus.IN_PROGRESS)

    def test_update_task_status_no_parent_job(self, subject, mock_job_repo, mock_chunk_repo):
        mock_chunk_repo.get_job_id_for_chunk.return_value = None

        subject.update_task_status(10, ChunkStatus.DOWNLOADED, "done")

        mock_chunk_repo.update_status.assert_called_once_with(10, ChunkStatus.DOWNLOADED, "done")
        mock_job_repo.update_status.assert_not_called()
