"""Unit tests for repository layer."""
import pytest
from unittest.mock import Mock, MagicMock
import sqlite3

from backend.repositories import JobRepository, ChunkRepository
from backend.models import JobStatus, ChunkStatus


class TestJobRepository:
    """Tests for JobRepository."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = Mock()
        return db

    @pytest.fixture
    def subject(self, mock_db):
        """Create a JobRepository instance."""
        return JobRepository(mock_db)

    def test_create(self, subject, mock_db):
        """Test creating a new job."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.lastrowid = 123
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        job_id = subject.create(
            job_id="test-job",
            user_id="user-123",
            timestamp="20240101T120000",
            auth_user="0",
            cookie="test-cookie",
            total_chunks=5,
        )

        assert job_id == 123
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_get_by_id(self, subject, mock_db):
        """Test getting a job by ID."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_row = {"id": 1, "job_id": "test-job"}
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        result = subject.get_by_id(1)

        assert result == mock_row
        mock_cursor.execute.assert_called_with("SELECT * FROM jobs WHERE id = ?", (1,))
        mock_conn.close.assert_called_once()

    def test_list_all(self, subject, mock_db):
        """Test listing all jobs."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_rows = [
            {"id": 1, "job_id": "job-1"},
            {"id": 2, "job_id": "job-2"},
        ]
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        result = subject.list_all()

        assert result == mock_rows
        mock_conn.close.assert_called_once()

    def test_update_status(self, subject, mock_db):
        """Test updating job status."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        subject.update_status(1, JobStatus.COMPLETED)

        mock_cursor.execute.assert_called_with(
            "UPDATE jobs SET status = ? WHERE id = ?",
            (JobStatus.COMPLETED.value, 1),
        )
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_update_cookie(self, subject, mock_db):
        """Test updating job cookie."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        subject.update_cookie(1, "new-cookie")

        mock_cursor.execute.assert_called_with(
            "UPDATE jobs SET cookie = ? WHERE id = ?",
            ("new-cookie", 1),
        )
        mock_conn.commit.assert_called_once()


class TestChunkRepository:
    """Tests for ChunkRepository."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = Mock()
        return db

    @pytest.fixture
    def subject(self, mock_db):
        """Create a ChunkRepository instance."""
        return ChunkRepository(mock_db)

    def test_create_chunks_for_job(self, subject, mock_db):
        """Test creating chunks for a job."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        subject.create_chunks_for_job(job_id=1, total_chunks=3)

        # Should be called 3 times (once per chunk)
        assert mock_cursor.execute.call_count == 3
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_get_by_id(self, subject, mock_db):
        """Test getting a chunk by ID."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_row = {"id": 1, "chunk_index": 1, "status": ChunkStatus.PENDING_DOWNLOAD.value}
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        result = subject.get_by_id(1)

        assert result == mock_row
        mock_cursor.execute.assert_called_with("SELECT * FROM chunks WHERE id = ?", (1,))

    def test_get_next_pending_download(self, subject, mock_db):
        """Test getting next pending download chunk."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda k: {
            "id": 1,
            "job_id": "test-job",
            "user_id": "user-1",
            "timestamp": "20240101T120000",
            "auth_user": "0",
            "cookie": "test-cookie",
            "chunk_index": 1,
        }[k])
        mock_row.keys.return_value = ["id", "job_id", "user_id", "timestamp", "auth_user", "cookie", "chunk_index"]
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        result = subject.get_next_pending_download()

        assert result is not None
        assert result["id"] == 1
        mock_conn.close.assert_called_once()

    def test_update_status(self, subject, mock_db):
        """Test updating chunk status."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        subject.update_status(1, ChunkStatus.DOWNLOADED, "Download complete")

        mock_cursor.execute.assert_called_with(
            "UPDATE chunks SET status = ?, message = ? WHERE id = ?",
            (ChunkStatus.DOWNLOADED.value, "Download complete", 1),
        )
        mock_conn.commit.assert_called_once()

    def test_get_status_counts_for_job(self, subject, mock_db):
        """Test getting chunk status counts."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_rows = [
            {"status": ChunkStatus.DOWNLOADED.value, "count": 2},
            {"status": ChunkStatus.EXTRACTED.value, "count": 3},
        ]
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        result = subject.get_status_counts_for_job(1)

        assert result == {
            ChunkStatus.DOWNLOADED.value: 2,
            ChunkStatus.EXTRACTED.value: 3,
        }
        mock_conn.close.assert_called_once()

    def test_list_for_job(self, subject, mock_db):
        """Test listing chunks for a job."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_rows = [
            Mock(__getitem__=Mock(side_effect=lambda k: {"id": 1, "chunk_index": 1, "status": "downloaded", "message": ""}[k]),
                 keys=Mock(return_value=["id", "chunk_index", "status", "message"])),
            Mock(__getitem__=Mock(side_effect=lambda k: {"id": 2, "chunk_index": 2, "status": "extracted", "message": ""}[k]),
                 keys=Mock(return_value=["id", "chunk_index", "status", "message"])),
        ]
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        result = subject.list_for_job(1)

        assert len(result) == 2
        assert result[0]["chunk_index"] == 1
        assert result[1]["chunk_index"] == 2

    def test_reset_to_pending_download(self, subject, mock_db):
        """Test resetting chunk to pending_download."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        subject.reset_to_pending_download(1)

        assert ChunkStatus.PENDING_DOWNLOAD.value in str(mock_cursor.execute.call_args)
        mock_conn.commit.assert_called_once()
