from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class Movement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service: str
    engine: str
    started_at: str
    finished_at: str
    outcome: str
    bytes_written: int
    bristol_type: Optional[int] = None
    sample_path: Optional[str] = None
    receipt_path: Optional[str] = None
    app_image: Optional[str] = None
    app_digest: Optional[str] = None
