from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
import sqlite3

from backend.containers import ManagerContainer
from backend.db import Database
from backend.models import TakeoutJob, TaskStatus, JobStatus, ChunkStatus, CookieUpdate

router = APIRouter()


@router.post("/api/jobs")
@inject
def create_job(
    job: TakeoutJob, db: Database = Depends(Provide[ManagerContainer.database])
):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (job_id, user_id, timestamp, auth_user, cookie, total_chunks, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            job.job_id,
            job.user_id,
            job.timestamp,
            job.auth_user,
            job.cookie,
            job.total_chunks,
            JobStatus.PENDING.value,
        ),
    )
    new_job_id = cursor.lastrowid

    for i in range(job.total_chunks):
        cursor.execute(
            "INSERT INTO chunks (job_id, chunk_index, status) VALUES (?, ?, ?)",
            (new_job_id, i + 1, ChunkStatus.PENDING_DOWNLOAD.value),
        )

    conn.commit()
    conn.close()
    return {
        "message": f"Job created successfully and {job.total_chunks} chunks queued."
    }


@router.get("/api/tasks/next")
@inject
def get_next_task(db: Database = Depends(Provide[ManagerContainer.database])):
    conn = db.get_connection()
    cursor = conn.cursor()

    # 1. Prioritize pending downloads
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
        if row:
            conn.close()
            return {
                "id": row["id"],
                "type": "download",
                "params": {
                    "job_id": row["job_id"], "user_id": row["user_id"],
                    "timestamp": row["timestamp"], "auth_user": row["auth_user"],
                    "chunk_index": row["chunk_index"], "cookie": row["cookie"],
                },
            }
    except sqlite3.OperationalError:
        row = None # Should not happen if tables are created

    # 2. If no pending downloads, look for downloaded chunks to extract
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
            # Mark the chunk as "pending_extraction" to avoid re-assigning it
            cursor.execute("UPDATE chunks SET status = ? WHERE id = ?", (ChunkStatus.PENDING_EXTRACTION.value, row["id"]))
            conn.commit()
            conn.close()
            return {
                "id": row["id"],
                "type": "extract",
                "params": {
                    "job_id": row["job_id"],
                    "chunk_index": row["chunk_index"],
                    "timestamp": row["timestamp"],
                },
            }
    except sqlite3.OperationalError:
        row = None

    conn.close()
    return {"task": "none"}


@router.post("/api/tasks/{task_id}/status")
@inject
def update_task_status(
    task_id: int,
    status_update: TaskStatus,
    db: Database = Depends(Provide[ManagerContainer.database]),
):
    conn = db.get_connection()
    cursor = conn.cursor()

    # 1. Update the specific chunk status
    cursor.execute(
        "UPDATE chunks SET status = ?, message = ? WHERE id = ?",
        (status_update.status.value, status_update.message, task_id),
    )
    conn.commit()

    # 2. Get parent job_id
    cursor.execute("SELECT job_id FROM chunks WHERE id = ?", (task_id,))
    job_id_row = cursor.fetchone()
    if not job_id_row:
        conn.close()
        return {"message": "Status received, but no parent job found"}

    job_id = job_id_row["job_id"]

    # 3. Determine overall job status
    cursor.execute("SELECT status FROM chunks WHERE job_id = ?", (job_id,))
    chunk_statuses = [row["status"] for row in cursor.fetchall()]

    if all(s == ChunkStatus.EXTRACTED.value for s in chunk_statuses):
        job_new_status = JobStatus.COMPLETED.value
    elif any(s == ChunkStatus.FAILED.value for s in chunk_statuses):
        job_new_status = JobStatus.FAILED.value
    else:
        job_new_status = JobStatus.IN_PROGRESS.value

    # 4. Update job status
    cursor.execute(
        "UPDATE jobs SET status = ? WHERE id = ?",
        (job_new_status, job_id),
    )
    conn.commit()
    conn.close()
    return {"message": "Status received"}


@router.get("/api/jobs")
@inject
def list_jobs(db: Database = Depends(Provide[ManagerContainer.database])):
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
    jobs = cursor.fetchall()

    result = []
    for job in jobs:
        job_id = job["id"]

        # Get chunk statistics
        cursor.execute(
            f"SELECT status, COUNT(*) as count FROM chunks WHERE job_id = ? GROUP BY status",
            (job_id,)
        )
        chunk_stats = {row["status"]: row["count"] for row in cursor.fetchall()}

        total_chunks = job["total_chunks"]
        extracted = chunk_stats.get(ChunkStatus.EXTRACTED.value, 0)
        downloaded = chunk_stats.get(ChunkStatus.DOWNLOADED.value, 0) + chunk_stats.get(ChunkStatus.PENDING_EXTRACTION.value, 0)
        failed = chunk_stats.get(ChunkStatus.FAILED.value, 0)
        completed = extracted
        progress = int((completed / total_chunks * 100)) if total_chunks > 0 else 0

        result.append({
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
            "progress": progress
        })

    conn.close()
    return result


@router.get("/api/jobs/{job_id}/chunks")
@inject
def get_job_chunks(job_id: int, db: Database = Depends(Provide[ManagerContainer.database])):
    conn = db.get_connection()
    cursor = conn.cursor()

    # Verify job exists
    cursor.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")

    # Get all chunks for this job
    cursor.execute(
        "SELECT id, chunk_index, status, message FROM chunks WHERE job_id = ? ORDER BY chunk_index",
        (job_id,)
    )
    chunks = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return chunks


@router.post("/api/jobs/{job_id}/cookie")
@inject
def update_job_cookie(
    job_id: int,
    cookie_update: CookieUpdate,
    db: Database = Depends(Provide[ManagerContainer.database])
):
    conn = db.get_connection()
    cursor = conn.cursor()

    # Verify job exists
    cursor.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")

    # Update the cookie
    cursor.execute(
        "UPDATE jobs SET cookie = ? WHERE id = ?",
        (cookie_update.cookie, job_id)
    )
    conn.commit()
    conn.close()

    return {"message": "Cookie updated successfully"}


@router.post("/api/jobs/{job_id}/retry-failed")
@inject
def retry_failed_chunks(
    job_id: int,
    db: Database = Depends(Provide[ManagerContainer.database])
):
    conn = db.get_connection()
    cursor = conn.cursor()

    # Verify job exists
    cursor.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")

    # Get all failed chunks
    cursor.execute(
        f"SELECT id, chunk_index FROM chunks WHERE job_id = ? AND status = '{ChunkStatus.FAILED.value}'",
        (job_id,)
    )
    failed_chunks = cursor.fetchall()

    if not failed_chunks:
        conn.close()
        return {"message": "No failed chunks to retry", "retried_count": 0}

    # Reset failed chunks to pending_download
    retried_count = 0
    for chunk in failed_chunks:
        cursor.execute(
            f"UPDATE chunks SET status = '{ChunkStatus.PENDING_DOWNLOAD.value}', message = NULL WHERE id = ?",
            (chunk["id"],)
        )
        retried_count += 1

    # Update job status back to in_progress if it was failed
    cursor.execute(
        f"UPDATE jobs SET status = '{JobStatus.IN_PROGRESS.value}' WHERE id = ? AND status = '{JobStatus.FAILED.value}'",
        (job_id,)
    )

    conn.commit()
    conn.close()

    return {"message": f"Retrying {retried_count} failed chunks", "retried_count": retried_count}


@router.post("/api/chunks/{chunk_id}/retry")
@inject
def retry_single_chunk(
    chunk_id: int,
    db: Database = Depends(Provide[ManagerContainer.database])
):
    conn = db.get_connection()
    cursor = conn.cursor()

    # Verify chunk exists and get its status
    cursor.execute("SELECT id, status, job_id FROM chunks WHERE id = ?", (chunk_id,))
    chunk = cursor.fetchone()

    if not chunk:
        conn.close()
        raise HTTPException(status_code=404, detail="Chunk not found")

    # Reset chunk to pending_download
    cursor.execute(
        f"UPDATE chunks SET status = '{ChunkStatus.PENDING_DOWNLOAD.value}', message = NULL WHERE id = ?",
        (chunk_id,)
    )

    # Update job status back to in_progress if needed
    cursor.execute(
        f"UPDATE jobs SET status = '{JobStatus.IN_PROGRESS.value}' WHERE id = ? AND status = '{JobStatus.FAILED.value}'",
        (chunk["job_id"],)
    )

    conn.commit()
    conn.close()

    return {"message": "Chunk queued for retry"}
