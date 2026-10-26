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
    fetched = docker("exec", "-i", image_container, "/app/.venv/bin/python", "-", stdin="""
import asyncio
import subprocess
from warden.profiles.git import GitCatalog
from warden.profiles.settings import ProfileSettings
subprocess.run(['ssh', '-V'], check=True)
def git(*args):
    return subprocess.check_output(['git', '-C', '/tmp/catalog', *args], text=True).strip()
git('init', '-b', 'main')
git('add', '.')
git('-c', 'user.name=Image test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'fixture')
settings = ProfileSettings.from_env({'WARDEN_PROFILES_REPO': '/tmp/catalog'})
snapshot = asyncio.run(GitCatalog(settings).fetch())
assert snapshot.commit == git('rev-parse', 'HEAD')
assert len(snapshot.documents) == 2
print('image catalog loaded from Git on tmpfs')
""")
    assert fetched.returncode == 0, fetched.stderr
    assert fetched.stdout.strip() == "image catalog loaded from Git on tmpfs"
