"""Black-box e2e: run the real worker image's bundled gpth + exiftool binaries
against a synthetic Google Takeout export, through the actual GpthRunner class
(not a hand-copied command), and verify EXIF DateTime/GPS really get embedded
from the JSON sidecar with output organized into <year>/<month>/.

This exists because GpthRunner's flags were previously validated only by
reading GPTH Neo's docs, not by running the binary — which turned out to
matter: `gpth --help` hangs forever without stdin redirected to /dev/null, and
gpth requires the literal Takeout/Google Photos/Photos from YYYY/ structure
under --input or it refuses to run at all. Mocked unit/integration tests can't
catch either of those.

Drives a single container via the docker CLI directly (no compose needed).
Consumes a prebuilt image via $WORKER_IMAGE (set by CI); falls back to
building worker:e2e locally for dev runs. Invokes GpthRunner through `uv run`
inside the container, matching the real CMD, rather than the venv's own
python symlink directly (which points at a build-stage-only interpreter path
and only self-heals when invoked via `uv run`).
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent
STACK_ROOT = HERE.parents[1]  # tests/e2e -> tests -> worker (Dockerfile build context)
IMAGE = os.environ.get("WORKER_IMAGE", "worker:e2e")
CONTAINER = "worker-e2e-gpth"

# Smallest possible valid JPEG (1x1 pixel), base64-encoded.
_TINY_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8Q"
    "EBEQCgwSExIQEw8QEBD/2wBDAQMDAwQDBAgEBAgQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQ"
    "EBAQEBAQEBD/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAj/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QA"
    "FQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="
)


def _run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


@pytest.fixture(scope="module")
def container():
    if not os.environ.get("WORKER_IMAGE"):
        _run(["docker", "build", "-t", IMAGE, str(STACK_ROOT)])
    subprocess.run(["docker", "rm", "-f", CONTAINER], check=False, capture_output=True)
    _run(["docker", "create", "--name", CONTAINER, IMAGE, "sleep", "300"])
    _run(["docker", "start", CONTAINER])
    try:
        yield CONTAINER
    finally:
        subprocess.run(["docker", "rm", "-f", CONTAINER], check=False)


def _seed_synthetic_takeout(tmp_path: Path) -> Path:
    # gpth requires this literal Takeout/Google Photos/Photos from YYYY/ shape
    # under --input (a flat folder of the same files fails with ERROR_CODE_12) —
    # it matches what tar_runner.extract() unpacks from a real Takeout chunk archive.
    photos_dir = tmp_path / "Takeout" / "Google Photos" / "Photos from 2023"
    photos_dir.mkdir(parents=True)
    (photos_dir / "IMG_20230615_120000.jpg").write_bytes(base64.b64decode(_TINY_JPEG_B64))
    (photos_dir / "IMG_20230615_120000.jpg.json").write_text(json.dumps({
        "title": "IMG_20230615_120000.jpg",
        "photoTakenTime": {"timestamp": "1686830400", "formatted": "Jun 15, 2023"},
        "geoData": {"latitude": 37.7749, "longitude": -122.4194, "altitude": 10.0},
    }))
    return tmp_path


def test_gpth_runner_embeds_exif_from_json_sidecar(container, tmp_path):
    takeout_root = _seed_synthetic_takeout(tmp_path)

    _run(["docker", "exec", container, "rm", "-rf", "/tmp/input", "/tmp/output"])
    _run(["docker", "exec", container, "mkdir", "-p", "/tmp/input", "/tmp/output"])
    _run(["docker", "cp", f"{takeout_root}/.", f"{container}:/tmp/input"])

    result = subprocess.run(
        [
            "docker", "exec", "-w", "/app", container, "uv", "run", "python", "-c",
            "import asyncio\n"
            "from worker.runners import GpthRunner\n"
            "print(asyncio.run(GpthRunner().process('/tmp/input', '/tmp/output')))\n",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("True"), result.stdout + result.stderr

    find = subprocess.run(
        ["docker", "exec", container, "find", "/tmp/output", "-iname", "*.jpg"],
        capture_output=True, text=True, check=True,
    )
    output_path = find.stdout.strip()
    assert output_path == "/tmp/output/2023/06/IMG_20230615_120000.jpg", output_path

    exif = subprocess.run(
        ["docker", "exec", container, "exiftool", "-DateTimeOriginal", "-GPSLatitude", output_path],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "2023:06:15" in exif
    assert "37 deg" in exif
