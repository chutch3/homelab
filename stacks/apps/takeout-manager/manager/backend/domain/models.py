from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class JobRecord:
    id: int
    job_id: str
    timestamp: str
    total_chunks: int
    status: str
    cookie: str
    user_id: str
    auth_user: str
    metadata_status: Optional[str]
    metadata_message: Optional[str]


@dataclass(frozen=True)
class ChunkRecord:
    id: int
    job_id: int
    chunk_index: int
    status: str
    message: Optional[str]
    downloaded_bytes: int
    total_bytes: Optional[int]
    speed_bytes_per_sec: Optional[float]


@dataclass(frozen=True)
class DownloadTaskInfo:
    id: int
    job_id: str
    user_id: str
    timestamp: str
    auth_user: str
    cookie: str
    chunk_index: int


@dataclass(frozen=True)
class ExtractTaskInfo:
    id: int
    job_id: str
    chunk_index: int
    timestamp: str


@dataclass(frozen=True)
class MetadataTaskInfo:
    id: int
    job_id: str
    timestamp: str
    total_chunks: int
