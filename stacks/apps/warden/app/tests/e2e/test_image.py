"""Opt-in image check: set WARDEN_TEST_IMAGE and WARDEN_TEST_DOCKER_CONTEXT.

Uses an isolated container with no network or host mounts; never starts a Swarm
service or contacts real Arr instances. The image must already be built.
"""
from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest


pytestmark = pytest.mark.e2e
STACK = Path(__file__).resolve().parents[3]


def docker(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "--context", os.environ.get("WARDEN_TEST_DOCKER_CONTEXT", "default"), *args],
        input=stdin, capture_output=True, text=True, timeout=45,
    )


@pytest.fixture
def image_container() -> Iterator[str]:
    image = os.environ.get("WARDEN_TEST_IMAGE")
    if not image:
        pytest.skip("set WARDEN_TEST_IMAGE to run the isolated Docker image check")
    result = docker(
        "run", "--detach", "--network", "none", "--memory", "256m",
        "--tmpfs", "/state:rw,size=16m", "--tmpfs", "/profile-cache:rw,size=64m",
        "--env", "UV_HTTP_TIMEOUT=2", "--env", "UV_HTTP_RETRIES=0", image,
    )
    assert result.returncode == 0, result.stderr
    container = result.stdout.strip()
    try:
        yield container
    finally:
        cleanup = docker("rm", "--force", container)
        assert cleanup.returncode == 0, cleanup.stderr


def test_image_boots_offline_and_loads_git_catalog_on_tmpfs(image_container: str) -> None:
    health = docker("exec", "-i", image_container, "/app/.venv/bin/python", "-", stdin="""
import json
import time
from urllib.error import URLError
from urllib.request import urlopen
for attempt in range(40):
    try:
        with urlopen('http://127.0.0.1:9090/healthz', timeout=1) as response:
            print(response.read().decode())
        break
    except URLError:
        time.sleep(0.25)
else:
    raise AssertionError('image did not become healthy without network access')
""")
    assert health.returncode == 0, health.stderr + docker("logs", image_container).stdout + docker("logs", image_container).stderr
    assert json.loads(health.stdout) == {"status": "ok"}
    created = docker("exec", image_container, "mkdir", "/tmp/catalog")
    assert created.returncode == 0, created.stderr
    copied = docker("cp", str(STACK / "examples/profiles") + "/.", f"{image_container}:/tmp/catalog")
    assert copied.returncode == 0, copied.stderr
    prepared = docker("exec", "-i", image_container, "/app/.venv/bin/python", "-", stdin="""
import subprocess
subprocess.run(['ssh', '-V'], check=True)
def git(*args):
    return subprocess.check_output(['git', '-C', '/tmp/catalog', *args], text=True).strip()
git('init', '-b', 'main')
git('add', '.')
git('-c', 'user.name=Image test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'fixture')
print(git('rev-parse', 'HEAD'))
""")
    assert prepared.returncode == 0, prepared.stderr
    revision = prepared.stdout.strip()
    started = docker(
        "exec", "--detach", "--env", "WARDEN_PROFILES_REPO=/tmp/catalog",
        "--env", "WARDEN_RADARR_URL=http://127.0.0.1:1", "--env", "WARDEN_RADARR_API_KEY=test-key",
        "--env", "WARDEN_METRICS_PORT=9091", "--env", "WARDEN_DB_PATH=/state/observer.db",
        image_container, "/app/.venv/bin/warden", "serve",
    )
    assert started.returncode == 0, started.stderr
    observed = docker("exec", "-i", image_container, "/app/.venv/bin/python", "-", stdin="""
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
for attempt in range(60):
    try:
        with urlopen('http://127.0.0.1:9091/metrics', timeout=1) as response:
            metrics = response.read().decode()
        count = next(float(line.split()[1]) for line in metrics.splitlines()
                     if line.startswith('warden_profiles_cycle_duration_seconds_count '))
        if count >= 1:
            assert 'warden_profiles_enabled{source="radarr"} 1.0' in metrics
            assert 'warden_profiles_check_success{source="radarr"} 0.0' in metrics
            break
    except (URLError, StopIteration):
        pass
    time.sleep(0.25)
else:
    raise AssertionError('CLI observer did not complete a cycle')
snapshots = list(Path('/profile-cache').glob('snapshot-*'))
assert len(snapshots) == 1
print(snapshots[0])
""")
    assert observed.returncode == 0, observed.stderr
    snapshot = observed.stdout.strip()
    fetched = docker("exec", image_container, "git", "-C", snapshot, "rev-parse", "HEAD")
    assert fetched.returncode == 0, fetched.stderr
    assert fetched.stdout.strip() == revision
    validated = docker("exec", image_container, "/app/.venv/bin/warden", "profiles", "validate", "--directory", snapshot)
    assert validated.returncode == 0, validated.stderr
    assert validated.stdout == "Valid catalog: 1 profiles, 1 custom formats.\n"


def test_image_exposes_cli_and_bundled_schemas(image_container: str) -> None:
    help_result = docker("exec", image_container, "/app/.venv/bin/warden", "--help")
    assert help_result.returncode == 0, help_result.stderr
    assert "serve" in help_result.stdout and "profiles" in help_result.stdout
    created = docker("exec", image_container, "mkdir", "/tmp/catalog")
    assert created.returncode == 0, created.stderr
    copied = docker("cp", str(STACK / "examples/profiles") + "/.", f"{image_container}:/tmp/catalog")
    assert copied.returncode == 0, copied.stderr
    result = docker("exec", "--workdir", "/tmp", image_container, "/app/.venv/bin/warden",
                    "profiles", "validate", "--directory", "/tmp/catalog")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Valid catalog: 1 profiles, 1 custom formats.\n"
    config = docker("inspect", image_container, "--format", "{{json .Config}}")
    assert config.returncode == 0, config.stderr
    assert json.loads(config.stdout)["Entrypoint"] == ["/app/.venv/bin/warden"]
    assert json.loads(config.stdout)["Cmd"] == ["serve"]
