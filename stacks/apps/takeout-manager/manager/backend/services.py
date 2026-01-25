"""Service layer for business logic."""
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.models import JobStatus, ChunkStatus, TakeoutJob
from backend.repositories import JobRepository, ChunkRepository


class JobService:
    """Service for job-related business logic."""

    def __init__(self, job_repo: JobRepository, chunk_repo: ChunkRepository):
        self._job_repo = job_repo
        self._chunk_repo = chunk_repo
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_job(self, job: TakeoutJob) -> Dict[str, Any]:
        """Create a new job with all its chunks.

        Args:
            job: Job data

        Returns:
            Dict with success message and chunk count
        """
        # Create the job
        new_job_id = self._job_repo.create(
            job_id=job.job_id,
            user_id=job.user_id,
            timestamp=job.timestamp,
            auth_user=job.auth_user,
            cookie=job.cookie,
            total_chunks=job.total_chunks,
        )

        # Create all chunks for the job
        self._chunk_repo.create_chunks_for_job(new_job_id, job.total_chunks)

        self.logger.info(
            f"Created job with {job.total_chunks} chunks",
            extra={"job_id": new_job_id, "total_chunks": job.total_chunks},
        )

        return {
            "message": f"Job created successfully and {job.total_chunks} chunks queued.",
            "job_id": new_job_id,
        }

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all jobs with their statistics.

        Returns:
            List of job dicts with chunk statistics
        """
        jobs = self._job_repo.list_all()
        result = []

        for job in jobs:
            job_id = job["id"]
            total_chunks = job["total_chunks"]

            # Get chunk statistics
            chunk_stats = self._chunk_repo.get_status_counts_for_job(job_id)

            extracted = chunk_stats.get(ChunkStatus.EXTRACTED.value, 0)
            downloaded = (
                chunk_stats.get(ChunkStatus.DOWNLOADED.value, 0)
                + chunk_stats.get(ChunkStatus.PENDING_EXTRACTION.value, 0)
            )
            failed = chunk_stats.get(ChunkStatus.FAILED.value, 0)
            completed = extracted
            progress = int((completed / total_chunks * 100)) if total_chunks > 0 else 0

            result.append(
                {
                    "id": job_id,
                    "job_id": job["job_id"],
                    "user_id": job["user_id"],
                    "timestamp": job["timestamp"],
                    "total_chunks": total_chunks,
                    "status": job["status"],
                    "downloaded_chunks": downloaded,
                    "extracted_chunks": extracted,
                    "failed_chunks": failed,
                    "completed_chunks": completed,
                    "progress": progress,
                }
            )

        return result

    def update_cookie(self, job_id: int, cookie: str) -> None:
        """Update the cookie for a job.

        Args:
            job_id: Database ID of the job
            cookie: New cookie value

        Raises:
            ValueError: If job not found
        """
        job = self._job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        self._job_repo.update_cookie(job_id, cookie)
        self.logger.info(f"Updated cookie for job", extra={"job_id": job_id})

    def retry_failed_chunks(self, job_id: int) -> Dict[str, Any]:
        """Retry all failed chunks for a job.

        Args:
            job_id: Database ID of the job

        Returns:
            Dict with message and count of retried chunks

        Raises:
            ValueError: If job not found
        """
        job = self._job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Get all failed chunks
        failed_chunks = self._chunk_repo.get_failed_for_job(job_id)

        if not failed_chunks:
            return {"message": "No failed chunks to retry", "retried_count": 0}

        # Reset each failed chunk to pending_download
        for chunk in failed_chunks:
            self._chunk_repo.reset_to_pending_download(chunk["id"])

        retried_count = len(failed_chunks)

        # Update job status back to in_progress if it was failed
        self._job_repo.update_status_if_failed(job_id, JobStatus.IN_PROGRESS)

        self.logger.info(
            f"Retrying {retried_count} failed chunks",
            extra={"job_id": job_id, "retried_count": retried_count},
        )

        return {
            "message": f"Retrying {retried_count} failed chunks",
            "retried_count": retried_count,
        }


class ChunkService:
    """Service for chunk-related business logic."""

    def __init__(self, job_repo: JobRepository, chunk_repo: ChunkRepository):
        self._job_repo = job_repo
        self._chunk_repo = chunk_repo
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_chunks_for_job(self, job_id: int) -> List[Dict[str, Any]]:
        """Get all chunks for a job.

        Args:
            job_id: Database ID of the job

        Returns:
            List of chunk dicts

        Raises:
            ValueError: If job not found
        """
        job = self._job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        return self._chunk_repo.list_for_job(job_id)

    def retry_chunk(self, chunk_id: int) -> None:
        """Retry a single chunk.

        Args:
            chunk_id: Database ID of the chunk

        Raises:
            ValueError: If chunk not found
        """
        chunk = self._chunk_repo.get_by_id(chunk_id)
        if not chunk:
            raise ValueError(f"Chunk {chunk_id} not found")

        # Reset chunk to pending_download
        self._chunk_repo.reset_to_pending_download(chunk_id)

        # Update parent job status if needed
        job_id = chunk["job_id"]
        self._job_repo.update_status_if_failed(job_id, JobStatus.IN_PROGRESS)

        self.logger.info(
            f"Retrying chunk",
            extra={"chunk_id": chunk_id, "job_id": job_id},
        )


class TaskService:
    """Service for task queue operations."""

    def __init__(self, job_repo: JobRepository, chunk_repo: ChunkRepository):
        self._job_repo = job_repo
        self._chunk_repo = chunk_repo
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_next_task(self) -> Dict[str, Any]:
        """Get the next available task from the queue.

        Returns:
            Task dict with type and params, or {"task": "none"} if no tasks
        """
        # 1. Prioritize pending downloads
        download_task = self._chunk_repo.get_next_pending_download()
        if download_task:
            self.logger.debug(
                f"Assigned download task",
                extra={
                    "task_id": download_task["id"],
                    "chunk_index": download_task["chunk_index"],
                },
            )
            return {
                "id": download_task["id"],
                "type": "download",
                "params": {
                    "job_id": download_task["job_id"],
                    "user_id": download_task["user_id"],
                    "timestamp": download_task["timestamp"],
                    "auth_user": download_task["auth_user"],
                    "chunk_index": download_task["chunk_index"],
                    "cookie": download_task["cookie"],
                },
            }

        # 2. If no pending downloads, look for downloaded chunks to extract
        extract_task = self._chunk_repo.get_next_downloaded()
        if extract_task:
            self.logger.debug(
                f"Assigned extract task",
                extra={
                    "task_id": extract_task["id"],
                    "chunk_index": extract_task["chunk_index"],
                },
            )
            return {
                "id": extract_task["id"],
                "type": "extract",
                "params": {
                    "job_id": extract_task["job_id"],
                    "chunk_index": extract_task["chunk_index"],
                    "timestamp": extract_task["timestamp"],
                },
            }

        # No tasks available
        return {"task": "none"}

    def update_task_status(
        self, task_id: int, status: ChunkStatus, message: str = ""
    ) -> None:
        """Update the status of a task and recalculate parent job status.

        Args:
            task_id: Database ID of the chunk/task
            status: New chunk status
            message: Optional status message
        """
        # 1. Update the specific chunk status
        self._chunk_repo.update_status(task_id, status, message)

        # 2. Get parent job_id
        job_id = self._chunk_repo.get_job_id_for_chunk(task_id)
        if not job_id:
            self.logger.warning(f"No parent job found for task {task_id}")
            return

        # 3. Determine overall job status based on chunk statuses
        chunk_statuses = self._chunk_repo.get_all_statuses_for_job(job_id)
        new_job_status = self._calculate_job_status(chunk_statuses)

        # 4. Update job status
        self._job_repo.update_status(job_id, new_job_status)

        self.logger.info(
            f"Updated task status",
            extra={
                "task_id": task_id,
                "status": status.value,
                "job_id": job_id,
                "job_status": new_job_status.value,
            },
        )

    def _calculate_job_status(self, chunk_statuses: List[str]) -> JobStatus:
        """Calculate overall job status based on chunk statuses.

        Args:
            chunk_statuses: List of chunk status values

        Returns:
            Calculated job status
        """
        if all(s == ChunkStatus.EXTRACTED.value for s in chunk_statuses):
            return JobStatus.COMPLETED
        elif any(s == ChunkStatus.FAILED.value for s in chunk_statuses):
            return JobStatus.FAILED
        else:
            return JobStatus.IN_PROGRESS
