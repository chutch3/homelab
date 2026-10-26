from __future__ import annotations

from pathlib import Path
import shlex

import pytest
import yaml


pytestmark = pytest.mark.integration
STACK = Path(__file__).resolve().parents[3]


def test_profile_cache_is_size_limited_tmpfs_separate_from_state() -> None:
    service = yaml.safe_load((STACK / "docker-compose.yml").read_text())["services"]["warden"]
    mounts = [mount for mount in service["volumes"] if isinstance(mount, dict)]
    assert {"type": "tmpfs", "target": "/profile-cache", "tmpfs": {"size": 67108864}} in mounts
    assert "WARDEN_PROFILES_REPO=${WARDEN_PROFILES_REPO:-}" in service["environment"]
    assert "WARDEN_PROFILES_MODE=${WARDEN_PROFILES_MODE:-observe}" in service["environment"]
    assert "WARDEN_RADARR_PROFILES" in service["environment"]
    assert "WARDEN_SONARR_PROFILES" in service["environment"]
    assert not any(entry.startswith("WARDEN_RADARR_PROFILES=") for entry in service["environment"])


def test_image_does_not_write_python_bytecode_at_runtime() -> None:
    assert "ENV PYTHONDONTWRITEBYTECODE=1" in (STACK / "app/Dockerfile").read_text()


def test_image_installs_git_and_ssh_for_profile_repositories() -> None:
    dockerfile = (STACK / "app/Dockerfile").read_text().replace("\\\n", " ")
    installs = [line for line in dockerfile.splitlines() if line.startswith("RUN ") and "apt-get install" in line]
    packages = {token for line in installs for token in shlex.split(line)}
    assert {"git", "openssh-client"} <= packages


def test_directory_catalog_uses_a_read_only_node_local_volume() -> None:
    compose = yaml.safe_load((STACK / "docker-compose.yml").read_text())
    service = compose['services']['warden']
    assert 'WARDEN_PROFILES_DIRECTORY=${WARDEN_PROFILES_DIRECTORY:-}' in service['environment']
    assert 'profiles:/profiles:ro' in service['volumes']
    assert compose['volumes']['profiles'] == {'driver': 'local'}
