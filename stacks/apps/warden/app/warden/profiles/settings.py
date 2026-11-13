from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from warden.settings import EnvironmentSettings


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


class ProfileSettings(EnvironmentSettings):
    model_config = SettingsConfigDict(env_prefix="WARDEN_PROFILES_")

    repo: str = ""
    ref: str = "main"
    path: str = "."
    cache: Path = Field(default=Path("/profile-cache"), validation_alias="WARDEN_PROFILES_CACHE_DIR")
    interval: float = Field(default=900, gt=0, allow_inf_nan=False, validation_alias="WARDEN_PROFILES_INTERVAL_SEC")
    timeout: float = Field(default=60, gt=0, allow_inf_nan=False, validation_alias="WARDEN_PROFILES_TIMEOUT_SEC")
    max_bytes: int = Field(default=32 * 1024 * 1024, gt=0, validation_alias="WARDEN_PROFILES_CACHE_MAX_BYTES")
    directory: Path | None = None
    mode: Literal["observe"] = "observe"

    @field_validator("directory", mode="before")
    @classmethod
    def empty_directory(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        if self.repo and self.directory:
            raise ValueError("WARDEN_PROFILES_REPO and WARDEN_PROFILES_DIRECTORY are mutually exclusive")
        if self.directory is not None and (not self.directory.is_absolute() or ".." in self.directory.parts):
            raise ValueError("profile directory must be an absolute unambiguous path")
        return self

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, repo: str) -> str:
        parsed = urlsplit(repo)
        if (repo.startswith("-") or "\n" in repo or parsed.password or parsed.query or parsed.fragment
                or (parsed.scheme in {"http", "https"} and parsed.username)):
            raise ValueError("repository must not contain options, query parameters, or embedded credentials")
        if repo and not (parsed.scheme in {"https", "ssh", "file"} or repo.startswith("/") or re.fullmatch(r"[\w.-]+@[\w.-]+:.+", repo)):
            raise ValueError("repository must use HTTPS, SSH, or an absolute local path")
        return repo

    @field_validator("ref")
    @classmethod
    def validate_ref(cls, ref: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", ref) or ".." in ref or "//" in ref:
            raise ValueError("invalid repository ref")
        return ref

    @field_validator("path")
    @classmethod
    def validate_path(cls, path: str) -> str:
        if not path or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
            raise ValueError("profile path must remain inside the repository")
        return path

    @field_validator("cache")
    @classmethod
    def validate_cache(cls, cache: Path) -> Path:
        if not cache.is_absolute():
            raise ValueError("profile cache must be an absolute path")
        return cache

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> ProfileSettings | None:
        if not env.get("WARDEN_PROFILES_REPO") and not env.get("WARDEN_PROFILES_DIRECTORY"):
            return None
        return cls(_environment=env)
