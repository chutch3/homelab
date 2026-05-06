import sqlite3
from typing import List, Optional, Dict, Any

from backend.db import Database
from backend.models import JobStatus, ChunkStatus


class JobRepository:
    def __init__(self, db: Database) -> None:
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
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        conn.close()
        return job

    def list_all(self) -> List[sqlite3.Row]:
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
        jobs = cursor.fetchall()
        conn.close()
        return jobs

    def update_status(self, job_id: int, status: JobStatus) -> None:
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status.value, job_id))
        conn.commit()
        conn.close()

    def update_cookie(self, job_id: int, cookie: str) -> None:
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET cookie = ? WHERE id = ?", (cookie, job_id))
        conn.commit()
        conn.close()

    def update_status_if_failed(self, job_id: int, new_status: JobStatus) -> None:
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET status = ? WHERE id = ? AND status = ?",
            (new_status.value, job_id, JobStatus.FAILED.value),
        )
        conn.commit()
        conn.close()


class ChunkRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create_chunks_for_job(self, job_id: int, total_chunks: int) -> None:
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
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
        chunk = cursor.fetchone()
        conn.close()
        return chunk

    def get_next_pending_download(self) -> Optional[Dict[str, Any]]:
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.id, j.job_id, j.user_id, j.timestamp, j.auth_user, j.cookie, c.chunk_index
                FROM chunks c JOIN jobs j ON c.job_id = j.id
                WHERE c.status = ?
                ORDER BY c.id
                LIMIT 1
                """,
                (ChunkStatus.PENDING_DOWNLOAD.value,),
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                cursor.execute(
                    "UPDATE chunks SET status = ? WHERE id = ?",
                    (ChunkStatus.DOWNLOADING.value, row["id"]),
                )
                conn.commit()
                return result
            return None
        finally:
            conn.close()

    def get_next_downloaded(self) -> Optional[Dict[str, Any]]:
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.id, j.job_id, c.chunk_index, j.timestamp
                FROM chunks c JOIN jobs j ON c.job_id = j.id
                WHERE c.status = ?
                ORDER BY c.id
                LIMIT 1
                """,
                (ChunkStatus.DOWNLOADED.value,),
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                cursor.execute(
                    "UPDATE chunks SET status = ? WHERE id = ?",
                    (ChunkStatus.PENDING_EXTRACTION.value, row["id"]),
                )
                conn.commit()
                return result
            return None
        finally:
            conn.close()

    def update_status(self, chunk_id: int, status: ChunkStatus, message: str = "") -> None:
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chunks SET status = ?, message = ? WHERE id = ?",
            (status.value, message, chunk_id),
        )
        conn.commit()
        conn.close()

    def get_job_id_for_chunk(self, chunk_id: int) -> Optional[int]:
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT job_id FROM chunks WHERE id = ?", (chunk_id,))
        row = cursor.fetchone()
        conn.close()
        return row["job_id"] if row else None

    def get_all_statuses_for_job(self, job_id: int) -> List[str]:
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM chunks WHERE job_id = ?", (job_id,))
        statuses = [row["status"] for row in cursor.fetchall()]
        conn.close()
        return statuses

    def get_status_counts_for_job(self, job_id: int) -> Dict[str, int]:
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
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, chunk_index FROM chunks WHERE job_id = ? AND status = ?",
            (job_id, ChunkStatus.FAILED.value),
        )
        failed = cursor.fetchall()
        conn.close()
        return failed

    def reset_to_pending_download(self, chunk_id: int) -> None:
        conn = self._db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chunks SET status = ?, message = NULL WHERE id = ?",
            (ChunkStatus.PENDING_DOWNLOAD.value, chunk_id),
        )
        conn.commit()
        conn.close()
