from __future__ import annotations

from pathlib import Path


class SecretReader:
    def __init__(self, base_dir: str = "/run/secrets") -> None:
        self._base = Path(base_dir)

    def read(self, name: str) -> str:
        return (self._base / name).read_text().strip()
