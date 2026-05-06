from pydantic import BaseModel
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ChunkStatus(str, Enum):
    PENDING_DOWNLOAD = "pending_download"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    PENDING_EXTRACTION = "pending_extraction"
    EXTRACTED = "extracted"
    FAILED = "failed"


class TakeoutJob(BaseModel):
    job_id: str
    user_id: str
    timestamp: str
    auth_user: str
    cookie: str
    total_chunks: int

class TaskStatus(BaseModel):
    status: ChunkStatus
    message: str = ""

class CookieUpdate(BaseModel):
    cookie: str
