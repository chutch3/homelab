from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str
    timestamp: str
    total_chunks: int
    status: str = "pending"
    cookie: str
    user_id: str
    auth_user: str
    metadata_status: Optional[str] = None
    metadata_message: Optional[str] = None


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id")
    chunk_index: int
    status: str = "pending_download"
    message: Optional[str] = None
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed_bytes_per_sec: Optional[float] = None
