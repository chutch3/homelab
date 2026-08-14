from __future__ import annotations

from collections.abc import Callable
from typing import Dict, List, Optional

from sqlmodel import select

from backend.db.models import Chunk as ChunkRow, Job as JobRow
from backend.domain.models import (
    ChunkRecord,
    DownloadTaskInfo,
    ExtractTaskInfo,
    JobRecord,
    MetadataTaskInfo,
)
from backend.models import ChunkStatus, JobStatus, MetadataStatus


def _to_job_record(row: JobRow) -> JobRecord:
    return JobRecord(
        id=row.id,
        job_id=row.job_id,
        timestamp=row.timestamp,
        total_chunks=row.total_chunks,
        status=row.status,
        cookie=row.cookie,
        user_id=row.user_id,
        auth_user=row.auth_user,
        metadata_status=row.metadata_status,
        metadata_message=row.metadata_message,
    )


def _to_chunk_record(row: ChunkRow) -> ChunkRecord:
    return ChunkRecord(
        id=row.id,
        job_id=row.job_id,
        chunk_index=row.chunk_index,
        status=row.status,
        message=row.message,
        downloaded_bytes=row.downloaded_bytes,
        total_bytes=row.total_bytes,
        speed_bytes_per_sec=row.speed_bytes_per_sec,
    )


class JobRepository:
    def __init__(self, session_factory: Callable) -> None:
        self._session_factory = session_factory

    def create(
        self,
        job_id: str,
        user_id: str,
        timestamp: str,
        auth_user: str,
        cookie: str,
        total_chunks: int,
    ) -> int:
        with self._session_factory() as session:
            row = JobRow(
                job_id=job_id,
                user_id=user_id,
                timestamp=timestamp,
                auth_user=auth_user,
                cookie=cookie,
                total_chunks=total_chunks,
                status=JobStatus.PENDING.value,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id

    def get_by_id(self, job_id: int) -> Optional[JobRecord]:
        with self._session_factory() as session:
            row = session.get(JobRow, job_id)
            return _to_job_record(row) if row else None

    def list_all(self) -> List[JobRecord]:
        with self._session_factory() as session:
            rows = session.exec(select(JobRow).order_by(JobRow.id.desc())).all()
            return [_to_job_record(row) for row in rows]

    def update_status(self, job_id: int, status: JobStatus) -> None:
        with self._session_factory() as session:
            row = session.get(JobRow, job_id)
            if row:
                row.status = status.value
                session.add(row)
                session.commit()

    def update_cookie(self, job_id: int, cookie: str) -> None:
        with self._session_factory() as session:
            row = session.get(JobRow, job_id)
            if row:
                row.cookie = cookie
                session.add(row)
                session.commit()

    def update_status_if_failed(self, job_id: int, new_status: JobStatus) -> None:
        with self._session_factory() as session:
            row = session.get(JobRow, job_id)
            if row and row.status == JobStatus.FAILED.value:
                row.status = new_status.value
                session.add(row)
                session.commit()

    def mark_metadata_pending(self, job_id: int) -> None:
        with self._session_factory() as session:
            row = session.get(JobRow, job_id)
            if row:
                row.metadata_status = MetadataStatus.PENDING.value
                row.metadata_message = None
                session.add(row)
                session.commit()

    def claim_next_pending_metadata_job(self) -> Optional[MetadataTaskInfo]:
        with self._session_factory() as session:
            row = session.exec(
                select(JobRow)
                .where(JobRow.metadata_status == MetadataStatus.PENDING.value)
                .order_by(JobRow.id)
                .limit(1)
            ).first()
            if not row:
                return None
            row.metadata_status = MetadataStatus.PROCESSING.value
            session.add(row)
            session.commit()
            return MetadataTaskInfo(
                id=row.id,
                job_id=row.job_id,
                timestamp=row.timestamp,
                total_chunks=row.total_chunks,
            )

    def update_metadata_status(self, job_id: int, status: MetadataStatus, message: str = "") -> None:
        with self._session_factory() as session:
            row = session.get(JobRow, job_id)
            if row:
                row.metadata_status = status.value
                row.metadata_message = message
                session.add(row)
                session.commit()


class ChunkRepository:
    def __init__(self, session_factory: Callable) -> None:
        self._session_factory = session_factory

    def create_chunks_for_job(self, job_id: int, total_chunks: int) -> None:
        with self._session_factory() as session:
            for i in range(total_chunks):
                session.add(
                    ChunkRow(
                        job_id=job_id,
                        chunk_index=i + 1,
                        status=ChunkStatus.PENDING_DOWNLOAD.value,
                    )
                )
            session.commit()

    def get_by_id(self, chunk_id: int) -> Optional[ChunkRecord]:
        with self._session_factory() as session:
            row = session.get(ChunkRow, chunk_id)
            return _to_chunk_record(row) if row else None

    def get_next_pending_download(self) -> Optional[DownloadTaskInfo]:
        with self._session_factory() as session:
            result = session.exec(
                select(ChunkRow, JobRow)
                .join(JobRow, ChunkRow.job_id == JobRow.id)  # type: ignore[arg-type]
                .where(ChunkRow.status == ChunkStatus.PENDING_DOWNLOAD.value)
                .order_by(ChunkRow.id)
                .limit(1)
            ).first()
            if not result:
                return None
            chunk_row, job_row = result
            chunk_row.status = ChunkStatus.DOWNLOADING.value
            session.add(chunk_row)
            session.commit()
            return DownloadTaskInfo(
                id=chunk_row.id,
                job_id=job_row.job_id,
                user_id=job_row.user_id,
                timestamp=job_row.timestamp,
                auth_user=job_row.auth_user,
                cookie=job_row.cookie,
                chunk_index=chunk_row.chunk_index,
            )

    def get_next_downloaded(self) -> Optional[ExtractTaskInfo]:
        with self._session_factory() as session:
            result = session.exec(
                select(ChunkRow, JobRow)
                .join(JobRow, ChunkRow.job_id == JobRow.id)  # type: ignore[arg-type]
                .where(ChunkRow.status == ChunkStatus.DOWNLOADED.value)
                .order_by(ChunkRow.id)
                .limit(1)
            ).first()
            if not result:
                return None
            chunk_row, job_row = result
            chunk_row.status = ChunkStatus.PENDING_EXTRACTION.value
            session.add(chunk_row)
            session.commit()
            return ExtractTaskInfo(
                id=chunk_row.id,
                job_id=job_row.job_id,
                chunk_index=chunk_row.chunk_index,
                timestamp=job_row.timestamp,
            )

    def update_status(self, chunk_id: int, status: ChunkStatus, message: str = "") -> None:
        with self._session_factory() as session:
            row = session.get(ChunkRow, chunk_id)
            if row:
                row.status = status.value
                row.message = message
                session.add(row)
                session.commit()

    def get_job_id_for_chunk(self, chunk_id: int) -> Optional[int]:
        with self._session_factory() as session:
            row = session.get(ChunkRow, chunk_id)
            return row.job_id if row else None

    def get_all_statuses_for_job(self, job_id: int) -> List[str]:
        with self._session_factory() as session:
            rows = session.exec(select(ChunkRow.status).where(ChunkRow.job_id == job_id)).all()
            return list(rows)

    def get_status_counts_for_job(self, job_id: int) -> Dict[str, int]:
        with self._session_factory() as session:
            statuses = session.exec(select(ChunkRow.status).where(ChunkRow.job_id == job_id)).all()
        counts: Dict[str, int] = {}
        for status in statuses:
            counts[status] = counts.get(status, 0) + 1
        return counts

    def list_for_job(self, job_id: int) -> List[ChunkRecord]:
        with self._session_factory() as session:
            rows = session.exec(
                select(ChunkRow).where(ChunkRow.job_id == job_id).order_by(ChunkRow.chunk_index)
            ).all()
            return [_to_chunk_record(row) for row in rows]

    def get_failed_for_job(self, job_id: int) -> List[ChunkRecord]:
        with self._session_factory() as session:
            rows = session.exec(
                select(ChunkRow).where(
                    ChunkRow.job_id == job_id, ChunkRow.status == ChunkStatus.FAILED.value
                )
            ).all()
            return [_to_chunk_record(row) for row in rows]

    def reset_to_pending_download(self, chunk_id: int) -> None:
        with self._session_factory() as session:
            row = session.get(ChunkRow, chunk_id)
            if row:
                row.status = ChunkStatus.PENDING_DOWNLOAD.value
                row.message = None
                session.add(row)
                session.commit()

    def reset_to_downloaded(self, chunk_id: int) -> None:
        with self._session_factory() as session:
            row = session.get(ChunkRow, chunk_id)
            if row:
                row.status = ChunkStatus.DOWNLOADED.value
                row.message = None
                session.add(row)
                session.commit()

    def update_progress(
        self,
        chunk_id: int,
        downloaded_bytes: int,
        total_bytes: Optional[int],
        speed_bytes_per_sec: float,
    ) -> None:
        with self._session_factory() as session:
            row = session.get(ChunkRow, chunk_id)
            if row:
                row.downloaded_bytes = downloaded_bytes
                row.total_bytes = total_bytes
                row.speed_bytes_per_sec = speed_bytes_per_sec
                session.add(row)
                session.commit()

    def get_progress_for_job(self, job_id: int) -> List[ChunkRecord]:
        with self._session_factory() as session:
            rows = session.exec(select(ChunkRow).where(ChunkRow.job_id == job_id)).all()
            return [_to_chunk_record(row) for row in rows]
