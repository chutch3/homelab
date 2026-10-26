from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


def parse_selection(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except ValueError as exc:
        raise ValueError("profile filter must be a JSON array of nonempty names") from exc
    if not isinstance(value, list) or any(not isinstance(name, str) or not name for name in value):
        raise ValueError("profile filter must be a JSON array of nonempty names")
    return value


@dataclass(frozen=True)
class ProfileSettings:
    repo: str
    ref: str
    path: str
    cache: Path
    interval: float
    timeout: float
    max_bytes: int
    directory: Path | None = None

    @staticmethod
    def from_env(env: Mapping[str, str]) -> ProfileSettings | None:
        repo = env.get("WARDEN_PROFILES_REPO", "")
        raw_directory = env.get("WARDEN_PROFILES_DIRECTORY", "")
        if repo and raw_directory:
            raise ValueError("WARDEN_PROFILES_REPO and WARDEN_PROFILES_DIRECTORY are mutually exclusive")
        directory = Path(raw_directory) if raw_directory else None
        if directory is not None and (not directory.is_absolute() or '..' in directory.parts):
            raise ValueError("profile directory must be an absolute unambiguous path")
        if not repo and directory is None:
            return None
        if env.get("WARDEN_PROFILES_MODE", "observe") != "observe":
            raise ValueError("WARDEN_PROFILES_MODE currently supports only observe")
        parsed = urlsplit(repo)
        if (repo.startswith("-") or "\n" in repo or parsed.password or parsed.query or parsed.fragment
                or (parsed.scheme in {"http", "https"} and parsed.username)):
            raise ValueError("repository must not contain options, query parameters, or embedded credentials")
        if repo and not (parsed.scheme in {"https", "ssh", "file"} or repo.startswith("/") or re.fullmatch(r"[\w.-]+@[\w.-]+:.+", repo)):
            raise ValueError("repository must use HTTPS, SSH, or an absolute local path")
        ref = env.get("WARDEN_PROFILES_REF", "main")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", ref) or ".." in ref or "//" in ref:
            raise ValueError("invalid repository ref")
        path = env.get("WARDEN_PROFILES_PATH", ".")
        if not path or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
            raise ValueError("profile path must remain inside the repository")
        try:
            interval = float(env.get("WARDEN_PROFILES_INTERVAL_SEC", "900"))
            timeout = float(env.get("WARDEN_PROFILES_TIMEOUT_SEC", "60"))
            max_bytes = int(env.get("WARDEN_PROFILES_CACHE_MAX_BYTES", str(32 * 1024 * 1024)))
        except ValueError as exc:
            raise ValueError("invalid profile interval, timeout, or cache size") from exc
        if any(not math.isfinite(value) or value <= 0 for value in (interval, timeout)) or max_bytes <= 0:
            raise ValueError("profile interval, timeout, and cache size must be positive and finite")
        cache = Path(env.get("WARDEN_PROFILES_CACHE_DIR", "/profile-cache"))
        if not cache.is_absolute():
            raise ValueError("profile cache must be an absolute path")
        return ProfileSettings(repo, ref, path, cache, interval, timeout, max_bytes, directory)
