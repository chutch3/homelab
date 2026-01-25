"""API endpoints - thin HTTP layer."""
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from backend.containers import ManagerContainer
from backend.models import TakeoutJob, TaskStatus, CookieUpdate
from backend.services import JobService, ChunkService, TaskService


router = APIRouter()


@router.post("/api/jobs")
@inject
def create_job(
    job: TakeoutJob,
    job_service: JobService = Depends(Provide[ManagerContainer.job_service]),
):
    """Create a new takeout job with all chunks."""
    result = job_service.create_job(job)
    return {"message": result["message"]}


@router.get("/api/jobs")
@inject
def list_jobs(
    job_service: JobService = Depends(Provide[ManagerContainer.job_service]),
):
    """List all jobs with their statistics."""
    return job_service.list_jobs()


@router.get("/api/jobs/{job_id}/chunks")
@inject
def get_job_chunks(
    job_id: int,
    chunk_service: ChunkService = Depends(Provide[ManagerContainer.chunk_service]),
):
    """Get all chunks for a specific job."""
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
    """Update the authentication cookie for a job."""
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
    """Retry all failed chunks for a job."""
    try:
        return job_service.retry_failed_chunks(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/chunks/{chunk_id}/retry")
@inject
def retry_single_chunk(
    chunk_id: int,
    chunk_service: ChunkService = Depends(Provide[ManagerContainer.chunk_service]),
):
    """Retry a single failed chunk."""
    try:
        chunk_service.retry_chunk(chunk_id)
        return {"message": "Chunk queued for retry"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/tasks/next")
@inject
def get_next_task(
    task_service: TaskService = Depends(Provide[ManagerContainer.task_service]),
):
    """Get the next available task from the queue."""
    return task_service.get_next_task()


@router.post("/api/tasks/{task_id}/status")
@inject
def update_task_status(
    task_id: int,
    status_update: TaskStatus,
    task_service: TaskService = Depends(Provide[ManagerContainer.task_service]),
):
    """Update the status of a task."""
    task_service.update_task_status(
        task_id, status_update.status, status_update.message
    )
    return {"message": "Status received"}
