from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ProfileDocument:
    source: Literal["radarr", "sonarr"]
    kind: Literal["profiles", "custom_formats"]
    path: str
    data: dict[str, Any]


@dataclass(frozen=True)
class ProfileSnapshot:
    commit: str
    documents: tuple[ProfileDocument, ...]
