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
    auto_extract: bool = True


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


class ArchiveExtraction(SQLModel, table=True):
    __tablename__ = "archive_extractions"

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    status: str = "pending_extraction"
    message: Optional[str] = None


class ArchiveTimeline(SQLModel, table=True):
    __tablename__ = "archive_timelines"

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    status: str = "pending"
    data: Optional[str] = None
