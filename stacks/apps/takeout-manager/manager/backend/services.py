import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.archive_scanner import ArchiveScanner
from backend.models import JobStatus, ChunkStatus, MetadataStatus, TakeoutJob
from backend.repositories import (
    ArchiveExtractionRepository,
    ArchiveTimelineRepository,
    JobRepository,
    ChunkRepository,
)
from backend.domain.models import ChunkRecord

_ARCHIVE_TIMESTAMP_RE = re.compile(r"(\d{8}T\d{6})Z")


class JobService:
    def __init__(self, job_repo: JobRepository, chunk_repo: ChunkRepository) -> None:
        self._job_repo = job_repo
        self._chunk_repo = chunk_repo
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    def create_job(self, job: TakeoutJob) -> Dict[str, Any]:
        new_job_id = self._job_repo.create(
            job_id=job.job_id,
            user_id=job.user_id,
            timestamp=job.timestamp,
            auth_user=job.auth_user,
            cookie=job.cookie,
            total_chunks=job.total_chunks,
            auto_extract=job.auto_extract,
        )
        self._chunk_repo.create_chunks_for_job(new_job_id, job.total_chunks)
        self.logger.info(
            "Created job",
            extra={"job_id": new_job_id, "total_chunks": job.total_chunks},
        )
        return {
            "message": f"Job created successfully and {job.total_chunks} chunks queued.",
            "job_id": new_job_id,
        }

    def list_jobs(self) -> List[Dict[str, Any]]:
        jobs = self._job_repo.list_all()
        result = []
        for job in jobs:
            job_id = job.id
            total_chunks = job.total_chunks
            chunk_stats = self._chunk_repo.get_status_counts_for_job(job_id)
            extracted = chunk_stats.get(ChunkStatus.EXTRACTED.value, 0)
            downloaded = (
                chunk_stats.get(ChunkStatus.DOWNLOADED.value, 0)
                + chunk_stats.get(ChunkStatus.PENDING_EXTRACTION.value, 0)
            )
            failed = chunk_stats.get(ChunkStatus.FAILED.value, 0)
            completed = extracted
            progress = int((completed / total_chunks * 100)) if total_chunks > 0 else 0
            byte_progress = self._calculate_job_progress(self._chunk_repo.get_progress_for_job(job_id))
            result.append(
                {
                    "id": job_id,
                    "job_id": job.job_id,
                    "user_id": job.user_id,
                    "timestamp": job.timestamp,
                    "total_chunks": total_chunks,
                    "status": job.status,
                    "downloaded_chunks": downloaded,
                    "extracted_chunks": extracted,
                    "failed_chunks": failed,
                    "completed_chunks": completed,
                    "progress": progress,
                    "metadata_status": job.metadata_status,
                    "metadata_message": job.metadata_message,
                    **byte_progress,
                }
            )
        return result

    def _calculate_job_progress(self, chunks: List[ChunkRecord]) -> Dict[str, Any]:
        total_downloaded_bytes = sum(c.downloaded_bytes or 0 for c in chunks)
        total_expected_bytes = sum(c.total_bytes or 0 for c in chunks)
        combined_speed_bytes_per_sec = sum(
            c.speed_bytes_per_sec or 0.0
            for c in chunks
            if c.status == ChunkStatus.DOWNLOADING.value
        )
        estimated_seconds_remaining = (
            (total_expected_bytes - total_downloaded_bytes) / combined_speed_bytes_per_sec
            if combined_speed_bytes_per_sec > 0
            else None
        )
        return {
            "total_downloaded_bytes": total_downloaded_bytes,
            "total_expected_bytes": total_expected_bytes,
            "combined_speed_bytes_per_sec": combined_speed_bytes_per_sec,
            "estimated_seconds_remaining": estimated_seconds_remaining,
        }

    def update_cookie(self, job_id: int, cookie: str) -> None:
        job = self._job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        self._job_repo.update_cookie(job_id, cookie)
        self.logger.info("Updated cookie for job", extra={"job_id": job_id})

    def retry_failed_chunks(self, job_id: int) -> Dict[str, Any]:
        job = self._job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        failed_chunks = self._chunk_repo.get_failed_for_job(job_id)
        if not failed_chunks:
            return {"message": "No failed chunks to retry", "retried_count": 0}
        for chunk in failed_chunks:
            self._chunk_repo.reset_to_pending_download(chunk.id)
        retried_count = len(failed_chunks)
        self._job_repo.update_status_if_failed(job_id, JobStatus.IN_PROGRESS)
        self.logger.info(
            "Retrying failed chunks",
            extra={"job_id": job_id, "retried_count": retried_count},
        )
        return {
            "message": f"Retrying {retried_count} failed chunks",
            "retried_count": retried_count,
        }

    def reprocess_metadata(self, job_id: int) -> None:
        job = self._job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        self._job_repo.mark_metadata_pending(job_id)
        self.logger.info("Re-driving metadata phase", extra={"job_id": job_id})


class ChunkService:
    def __init__(self, job_repo: JobRepository, chunk_repo: ChunkRepository) -> None:
        self._job_repo = job_repo
        self._chunk_repo = chunk_repo
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    def get_chunks_for_job(self, job_id: int) -> List[Dict[str, Any]]:
        job = self._job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        return self._chunk_repo.list_for_job(job_id)

    def retry_chunk(self, chunk_id: int) -> None:
        chunk = self._chunk_repo.get_by_id(chunk_id)
        if not chunk:
            raise ValueError(f"Chunk {chunk_id} not found")
        self._chunk_repo.reset_to_pending_download(chunk_id)
        job_id = chunk.job_id
        self._job_repo.update_status_if_failed(job_id, JobStatus.IN_PROGRESS)
        self.logger.info("Retrying chunk", extra={"chunk_id": chunk_id, "job_id": job_id})

    def update_progress(
        self, chunk_id: int, downloaded_bytes: int, total_bytes: Optional[int], speed_bytes_per_sec: float
    ) -> None:
        self._chunk_repo.update_progress(chunk_id, downloaded_bytes, total_bytes, speed_bytes_per_sec)

    def reextract_chunk(self, chunk_id: int) -> None:
        chunk = self._chunk_repo.get_by_id(chunk_id)
        if not chunk:
            raise ValueError(f"Chunk {chunk_id} not found")
        self._chunk_repo.reset_to_downloaded(chunk_id)
        job_id = chunk.job_id
        self._job_repo.update_status_if_failed(job_id, JobStatus.IN_PROGRESS)
        # Extraction is a single whole-export GPTH pass now, so re-extracting a
        # chunk re-runs that pass.
        self._job_repo.mark_metadata_pending(job_id)
        self.logger.info("Re-extracting chunk", extra={"chunk_id": chunk_id, "job_id": job_id})


class TaskService:
    def __init__(
        self,
        job_repo: JobRepository,
        chunk_repo: ChunkRepository,
        extraction_repo: ArchiveExtractionRepository,
        timeline_repo: ArchiveTimelineRepository,
    ) -> None:
        self._job_repo = job_repo
        self._chunk_repo = chunk_repo
        self._extraction_repo = extraction_repo
        self._timeline_repo = timeline_repo
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    def get_next_task(self) -> Dict[str, Any]:
        download_task = self._chunk_repo.get_next_pending_download()
        if download_task:
            self.logger.debug(
                "Assigned download task",
                extra={"task_id": download_task.id, "chunk_index": download_task.chunk_index},
            )
            return {
                "id": download_task.id,
                "type": "download",
                "params": {
                    "job_id": download_task.job_id,
                    "user_id": download_task.user_id,
                    "timestamp": download_task.timestamp,
                    "auth_user": download_task.auth_user,
                    "chunk_index": download_task.chunk_index,
                    "cookie": download_task.cookie,
                },
            }
        # No per-chunk extract phase: GPTH extracts the whole export in one pass,
        # dispatched once all chunks are downloaded.
        extract_task = self._job_repo.claim_next_pending_metadata_job()
        if extract_task:
            self.logger.debug("Assigned extract task", extra={"task_id": extract_task.id})
            return {
                "id": extract_task.id,
                "type": "extract",
                "params": {
                    "job_id": extract_task.job_id,
                    "timestamp": extract_task.timestamp,
                    "total_chunks": extract_task.total_chunks,
                },
            }
        archive_task = self._extraction_repo.get_next_pending()
        if archive_task:
            self.logger.debug("Assigned extract_archive task", extra={"task_id": archive_task.id})
            return {
                "id": archive_task.id,
                "type": "extract_archive",
                "params": {"filename": archive_task.filename},
            }
        timeline_task = self._timeline_repo.get_next_pending()
        if timeline_task:
            self.logger.debug("Assigned timeline task", extra={"task_id": timeline_task.id})
            return {
                "id": timeline_task.id,
                "type": "timeline",
                "params": {"filename": timeline_task.filename},
            }
        return {"task": "none"}

    def update_task_status(self, task_id: int, status: ChunkStatus, message: str = "") -> None:
        self._chunk_repo.update_status(task_id, status, message)
        job_id = self._chunk_repo.get_job_id_for_chunk(task_id)
        if not job_id:
            self.logger.warning("No parent job found for task %s", task_id)
            return
        job = self._job_repo.get_by_id(job_id)
        auto_extract = job.auto_extract if job else True
        chunk_statuses = self._chunk_repo.get_all_statuses_for_job(job_id)
        new_job_status = self._calculate_job_status(chunk_statuses, auto_extract)
        self._job_repo.update_status(job_id, new_job_status)
        # Once every chunk is downloaded, trigger the single GPTH extract pass
        # (unless the job opted out of extraction). The job stays in progress
        # until that pass reports back.
        if auto_extract and chunk_statuses and all(
            s == ChunkStatus.DOWNLOADED.value for s in chunk_statuses
        ):
            self._job_repo.mark_metadata_pending(job_id)
        self.logger.info(
            "Updated task status",
            extra={
                "task_id": task_id,
                "status": status.value,
                "job_id": job_id,
                "job_status": new_job_status.value,
            },
        )

    def update_metadata_task_status(self, job_id: int, status: MetadataStatus, message: str = "") -> None:
        self._job_repo.update_metadata_status(job_id, status, message)
        # The GPTH pass is the extraction, so its outcome is the job's outcome.
        if status == MetadataStatus.COMPLETED:
            self._job_repo.update_status(job_id, JobStatus.COMPLETED)
        elif status == MetadataStatus.FAILED:
            self._job_repo.update_status(job_id, JobStatus.FAILED)
        self.logger.info(
            "Updated extract task status",
            extra={"job_id": job_id, "status": status.value},
        )

    def _calculate_job_status(self, chunk_statuses: List[str], auto_extract: bool = True) -> JobStatus:
        # With auto-extract off, a downloaded chunk is a terminal success — the
        # job never enters the extract phase.
        success_statuses = {ChunkStatus.EXTRACTED.value}
        if not auto_extract:
            success_statuses = {ChunkStatus.DOWNLOADED.value, ChunkStatus.EXTRACTED.value}
        if all(s in success_statuses for s in chunk_statuses):
            return JobStatus.COMPLETED
        terminal_statuses = success_statuses | {ChunkStatus.FAILED.value}
        if all(s in terminal_statuses for s in chunk_statuses) and any(
            s == ChunkStatus.FAILED.value for s in chunk_statuses
        ):
            return JobStatus.FAILED
        return JobStatus.IN_PROGRESS


class ArchiveService:
    def __init__(
        self,
        scanner: ArchiveScanner,
        job_repo: JobRepository,
        chunk_repo: ChunkRepository,
        extraction_repo: ArchiveExtractionRepository,
        timeline_repo: ArchiveTimelineRepository,
    ) -> None:
        self._scanner = scanner
        self._job_repo = job_repo
        self._chunk_repo = chunk_repo
        self._extraction_repo = extraction_repo
        self._timeline_repo = timeline_repo

    def request_extraction(self, filename: str) -> int:
        on_disk = {archive.filename for archive in self._scanner.scan()}
        if filename not in on_disk:
            raise ValueError(f"Archive {filename} not found")
        return self._extraction_repo.create(filename)

    def update_extraction_status(self, extraction_id: int, status: str, message: str = "") -> None:
        self._extraction_repo.update_status(extraction_id, status, message)

    def delete_archive(self, filename: str) -> None:
        on_disk = {archive.filename for archive in self._scanner.scan()}
        if filename not in on_disk:
            raise ValueError(f"Archive {filename} not found")
        self._scanner.delete(filename)

    def request_timeline(self, filename: str) -> int:
        on_disk = {archive.filename for archive in self._scanner.scan()}
        if filename not in on_disk:
            raise ValueError(f"Archive {filename} not found")
        return self._timeline_repo.create(filename)

    def get_timeline(self, filename: str) -> Dict[str, Any]:
        record = self._timeline_repo.get_by_filename(filename)
        if not record:
            return {"status": "none", "months": None}
        months = json.loads(record.data) if record.data else None
        return {"status": record.status, "months": months}

    def save_timeline_result(self, filename: str, months: Dict[str, int]) -> None:
        self._timeline_repo.upsert_result(filename, json.dumps(months))

    def list_timelines(self) -> List[Dict[str, Any]]:
        result = []
        for record in self._timeline_repo.list_all():
            months = json.loads(record.data) if record.data else None
            result.append({"filename": record.filename, "status": record.status, "months": months})
        return result

    def list_archives(self) -> List[Dict[str, Any]]:
        tracked = self._tracked_chunk_statuses()
        archives = [
            {
                "filename": archive.filename,
                "size_bytes": archive.size_bytes,
                "export_timestamp": self._parse_timestamp(archive.filename),
                "source": "db" if archive.filename in tracked else "disk",
                "extract_status": tracked.get(archive.filename, "unknown"),
            }
            for archive in self._scanner.scan()
        ]
        return sorted(archives, key=lambda a: a["filename"])

    def _tracked_chunk_statuses(self) -> Dict[str, str]:
        statuses: Dict[str, str] = {}
        for job in self._job_repo.list_all():
            for chunk in self._chunk_repo.list_for_job(job.id):
                name = f"takeout-{job.timestamp}Z-1-{chunk.chunk_index:03d}.tgz"
                statuses[name] = chunk.status
        return statuses

    @staticmethod
    def _parse_timestamp(filename: str) -> Optional[str]:
        match = _ARCHIVE_TIMESTAMP_RE.search(filename)
        if not match:
            return None
        parsed = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        return parsed.isoformat().replace("+00:00", "Z")
