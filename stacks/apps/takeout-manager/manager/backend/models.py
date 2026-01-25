from pydantic import BaseModel
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ChunkStatus(str, Enum):
    PENDING_DOWNLOAD = "pending_download"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    PENDING_EXTRACTION = "pending_extraction"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TakeoutJob(BaseModel):
    job_id: str
    user_id: str
    timestamp: str
    auth_user: str
    cookie: str
    total_chunks: int

class TaskStatus(BaseModel):
    status: ChunkStatus # Use ChunkStatus Enum
    message: str

class CookieUpdate(BaseModel):
    cookie: str
