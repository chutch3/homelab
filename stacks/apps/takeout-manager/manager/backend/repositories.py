"""Repository layer for data access operations."""
import sqlite3
from typing import List, Optional, Dict, Any

from backend.models import JobStatus, ChunkStatus


class JobRepository:
    """Repository for Job-related database operations."""

    def __init__(self, db):
        self._db = db

    def create(
        self,
        job_id: str,
        user_id: str,
        timestamp: str,
        auth_user: str,
        cookie: str,
        total_chunks: int,
    ) -> int:
        """Create a new job.

        Args:
            job_id: Google Takeout job ID
            user_id: User ID
            timestamp: Timestamp
            auth_user: Auth user
            cookie: Authentication cookie
            total_chunks: Total number of chunks

        Returns:
            The ID of the newly created job
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (job_id, user_id, timestamp, auth_user, cookie, total_chunks, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, user_id, timestamp, auth_user, cookie, total_chunks, JobStatus.PENDING.value),
        )
        new_job_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return new_job_id

    def get_by_id(self, job_id: int) -> Optional[sqlite3.Row]:
        """Get a job by its database ID.

        Args:
            job_id: Database ID of the job

        Returns:
            Job row or None if not found
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        conn.close()
        return job

    def list_all(self) -> List[sqlite3.Row]:
        """List all jobs ordered by ID descending.

        Returns:
            List of job rows
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
        jobs = cursor.fetchall()
        conn.close()
        return jobs

    def update_status(self, job_id: int, status: JobStatus) -> None:
        """Update job status.

        Args:
            job_id: Database ID of the job
            status: New status
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status.value, job_id))
        conn.commit()
        conn.close()

    def update_cookie(self, job_id: int, cookie: str) -> None:
        """Update job cookie.

        Args:
            job_id: Database ID of the job
            cookie: New cookie value
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET cookie = ? WHERE id = ?", (cookie, job_id))
        conn.commit()
        conn.close()

    def update_status_if_failed(self, job_id: int, new_status: JobStatus) -> None:
        """Update job status only if it's currently FAILED.

        Args:
            job_id: Database ID of the job
            new_status: New status to set
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET status = ? WHERE id = ? AND status = ?",
            (new_status.value, job_id, JobStatus.FAILED.value),
        )
        conn.commit()
        conn.close()


class ChunkRepository:
    """Repository for Chunk-related database operations."""

    def __init__(self, db):
        self._db = db

    def create_chunks_for_job(self, job_id: int, total_chunks: int) -> None:
        """Create all chunks for a job.

        Args:
            job_id: Database ID of the parent job
            total_chunks: Number of chunks to create
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        for i in range(total_chunks):
            cursor.execute(
                "INSERT INTO chunks (job_id, chunk_index, status) VALUES (?, ?, ?)",
                (job_id, i + 1, ChunkStatus.PENDING_DOWNLOAD.value),
            )
        conn.commit()
        conn.close()

    def get_by_id(self, chunk_id: int) -> Optional[sqlite3.Row]:
        """Get a chunk by its ID.

        Args:
            chunk_id: Database ID of the chunk

        Returns:
            Chunk row or None if not found
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
        chunk = cursor.fetchone()
        conn.close()
        return chunk

    def get_next_pending_download(self) -> Optional[Dict[str, Any]]:
        """Get the next chunk that needs to be downloaded.

        Returns:
            Dict with chunk and job info, or None if no chunks available
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT c.id, j.job_id, j.user_id, j.timestamp, j.auth_user, j.cookie, c.chunk_index
                FROM chunks c JOIN jobs j ON c.job_id = j.id
                WHERE c.status = '{ChunkStatus.PENDING_DOWNLOAD.value}'
                ORDER BY c.id
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return dict(row)
            return None
        except sqlite3.OperationalError:
            conn.close()
            return None

    def get_next_downloaded(self) -> Optional[Dict[str, Any]]:
        """Get the next downloaded chunk that needs extraction.

        Returns:
            Dict with chunk and job info, or None if no chunks available
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT c.id, j.job_id, c.chunk_index, j.timestamp
                FROM chunks c JOIN jobs j ON c.job_id = j.id
                WHERE c.status = '{ChunkStatus.DOWNLOADED.value}'
                ORDER BY c.id
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Mark as pending_extraction to avoid re-assignment
                cursor.execute(
                    "UPDATE chunks SET status = ? WHERE id = ?",
                    (ChunkStatus.PENDING_EXTRACTION.value, row["id"]),
                )
                conn.commit()
                conn.close()
                return result
            conn.close()
            return None
        except sqlite3.OperationalError:
            conn.close()
            return None

    def update_status(self, chunk_id: int, status: ChunkStatus, message: str = "") -> None:
        """Update chunk status and message.

        Args:
            chunk_id: Database ID of the chunk
            status: New status
            message: Optional status message
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chunks SET status = ?, message = ? WHERE id = ?",
            (status.value, message, chunk_id),
        )
        conn.commit()
        conn.close()

    def get_job_id_for_chunk(self, chunk_id: int) -> Optional[int]:
        """Get the parent job ID for a chunk.

        Args:
            chunk_id: Database ID of the chunk

        Returns:
            Job ID or None if chunk not found
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT job_id FROM chunks WHERE id = ?", (chunk_id,))
        row = cursor.fetchone()
        conn.close()
        return row["job_id"] if row else None

    def get_all_statuses_for_job(self, job_id: int) -> List[str]:
        """Get all chunk statuses for a job.

        Args:
            job_id: Database ID of the job

        Returns:
            List of chunk status values
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM chunks WHERE job_id = ?", (job_id,))
        statuses = [row["status"] for row in cursor.fetchall()]
        conn.close()
        return statuses

    def get_status_counts_for_job(self, job_id: int) -> Dict[str, int]:
        """Get chunk status counts for a job.

        Args:
            job_id: Database ID of the job

        Returns:
            Dict mapping status to count
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, COUNT(*) as count FROM chunks WHERE job_id = ? GROUP BY status",
            (job_id,),
        )
        stats = {row["status"]: row["count"] for row in cursor.fetchall()}
        conn.close()
        return stats

    def list_for_job(self, job_id: int) -> List[Dict[str, Any]]:
        """List all chunks for a job.

        Args:
            job_id: Database ID of the job

        Returns:
            List of chunk dicts
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, chunk_index, status, message FROM chunks WHERE job_id = ? ORDER BY chunk_index",
            (job_id,),
        )
        chunks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return chunks

    def get_failed_for_job(self, job_id: int) -> List[sqlite3.Row]:
        """Get all failed chunks for a job.

        Args:
            job_id: Database ID of the job

        Returns:
            List of failed chunk rows
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id, chunk_index FROM chunks WHERE job_id = ? AND status = '{ChunkStatus.FAILED.value}'",
            (job_id,),
        )
        failed = cursor.fetchall()
        conn.close()
        return failed

    def reset_to_pending_download(self, chunk_id: int) -> None:
        """Reset a chunk to pending_download status.

        Args:
            chunk_id: Database ID of the chunk
        """
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE chunks SET status = '{ChunkStatus.PENDING_DOWNLOAD.value}', message = NULL WHERE id = ?",
            (chunk_id,),
        )
        conn.commit()
        conn.close()
