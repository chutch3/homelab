from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from backend.containers import ManagerContainer
from backend.models import TakeoutJob, TaskStatus, CookieUpdate, ChunkProgress, MetadataTaskStatus, ArchiveExtractionStatus, ArchiveTimelineResult
from backend.services import JobService, ChunkService, TaskService, ArchiveService


router = APIRouter()


@router.get("/api/archives")
@inject
def list_archives(
    archive_service: ArchiveService = Depends(Provide[ManagerContainer.archive_service]),
):
    return archive_service.list_archives()


@router.post("/api/archives/{filename}/extract")
@inject
def extract_archive(
    filename: str,
    archive_service: ArchiveService = Depends(Provide[ManagerContainer.archive_service]),
):
    try:
        archive_service.request_extraction(filename)
        return {"message": "Archive queued for extraction"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/archive-extractions/{extraction_id}/status")
@inject
def update_archive_extraction_status(
    extraction_id: int,
    status_update: ArchiveExtractionStatus,
    archive_service: ArchiveService = Depends(Provide[ManagerContainer.archive_service]),
):
    archive_service.update_extraction_status(
        extraction_id, status_update.status, status_update.message
    )
    return {"message": "Status received"}


@router.delete("/api/archives/{filename}")
@inject
def delete_archive(
    filename: str,
    archive_service: ArchiveService = Depends(Provide[ManagerContainer.archive_service]),
):
    try:
        archive_service.delete_archive(filename)
        return {"message": "Archive deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/archives/{filename}/timeline")
@inject
def request_archive_timeline(
    filename: str,
    archive_service: ArchiveService = Depends(Provide[ManagerContainer.archive_service]),
):
    try:
        archive_service.request_timeline(filename)
        return {"message": "Timeline requested"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/archives/{filename}/timeline")
@inject
def get_archive_timeline(
    filename: str,
    archive_service: ArchiveService = Depends(Provide[ManagerContainer.archive_service]),
):
    return archive_service.get_timeline(filename)


@router.post("/api/archives/{filename}/timeline-result")
@inject
def save_archive_timeline_result(
    filename: str,
    result: ArchiveTimelineResult,
    archive_service: ArchiveService = Depends(Provide[ManagerContainer.archive_service]),
):
    archive_service.save_timeline_result(filename, result.months)
    return {"message": "Timeline received"}


@router.get("/api/timelines")
@inject
def list_timelines(
    archive_service: ArchiveService = Depends(Provide[ManagerContainer.archive_service]),
):
    return archive_service.list_timelines()


@router.post("/api/jobs")
@inject
def create_job(
    job: TakeoutJob,
    job_service: JobService = Depends(Provide[ManagerContainer.job_service]),
):
    return job_service.create_job(job)


@router.get("/api/jobs")
@inject
def list_jobs(
    job_service: JobService = Depends(Provide[ManagerContainer.job_service]),
):
    return job_service.list_jobs()


@router.get("/api/jobs/{job_id}/chunks")
@inject
def get_job_chunks(
    job_id: int,
    chunk_service: ChunkService = Depends(Provide[ManagerContainer.chunk_service]),
):
    try:
        return chunk_service.get_chunks_for_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/jobs/{job_id}/cookie")
@inject
def update_job_cookie(
    job_id: int,
    cookie_update: CookieUpdate,
    job_service: JobService = Depends(Provide[ManagerContainer.job_service]),
):
    try:
        job_service.update_cookie(job_id, cookie_update.cookie)
        return {"message": "Cookie updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/jobs/{job_id}/retry-failed")
@inject
def retry_failed_chunks(
    job_id: int,
    job_service: JobService = Depends(Provide[ManagerContainer.job_service]),
):
    try:
        return job_service.retry_failed_chunks(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/jobs/{job_id}/reprocess-metadata")
@inject
def reprocess_metadata(
    job_id: int,
    job_service: JobService = Depends(Provide[ManagerContainer.job_service]),
):
    try:
        job_service.reprocess_metadata(job_id)
        return {"message": "Job queued for metadata re-processing"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/chunks/{chunk_id}/retry")
@inject
def retry_single_chunk(
    chunk_id: int,
    chunk_service: ChunkService = Depends(Provide[ManagerContainer.chunk_service]),
):
    try:
        chunk_service.retry_chunk(chunk_id)
        return {"message": "Chunk queued for retry"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/chunks/{chunk_id}/reextract")
@inject
def reextract_single_chunk(
    chunk_id: int,
    chunk_service: ChunkService = Depends(Provide[ManagerContainer.chunk_service]),
):
    try:
        chunk_service.reextract_chunk(chunk_id)
        return {"message": "Chunk queued for re-extraction"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/tasks/next")
@inject
def get_next_task(
    task_service: TaskService = Depends(Provide[ManagerContainer.task_service]),
):
    return task_service.get_next_task()


@router.post("/api/tasks/{task_id}/status")
@inject
def update_task_status(
    task_id: int,
    status_update: TaskStatus,
    task_service: TaskService = Depends(Provide[ManagerContainer.task_service]),
):
    task_service.update_task_status(
        task_id, status_update.status, status_update.message
    )
    return {"message": "Status received"}


@router.post("/api/jobs/{job_id}/metadata-status")
@inject
def update_metadata_task_status(
    job_id: int,
    status_update: MetadataTaskStatus,
    task_service: TaskService = Depends(Provide[ManagerContainer.task_service]),
):
    task_service.update_metadata_task_status(
        job_id, status_update.status, status_update.message
    )
    return {"message": "Status received"}


@router.post("/api/tasks/{task_id}/progress")
@inject
def update_task_progress(
    task_id: int,
    progress: ChunkProgress,
    chunk_service: ChunkService = Depends(Provide[ManagerContainer.chunk_service]),
):
    chunk_service.update_progress(
        task_id, progress.downloaded_bytes, progress.total_bytes, progress.speed_bytes_per_sec
    )
    return {"message": "Progress received"}
