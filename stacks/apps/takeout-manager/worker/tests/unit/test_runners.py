"""Unit tests for the subprocess adapter runners (CurlRunner, TarRunner).

These classes are the owned abstraction over the curl/tar subprocesses, so the
subprocess boundary is patched here at the adapter — the one place mocking a
system dep directly is appropriate. asyncio.sleep is patched to keep the retry
test fast.
"""

import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.runners import CurlRunner, TarRunner


class TestCurlRunner:
    @pytest.fixture
    def subject(self):
        return CurlRunner(max_retries=2)

    @pytest.mark.asyncio
    async def test_download_returns_true_on_success(self, subject):
        with patch("subprocess.run", return_value=MagicMock()) as run:
            result = await subject.download("https://x/y", "/tmp/out", {"k": "v"})
        assert result is True
        run.assert_called_once()
        cmd = run.call_args[0][0]
        assert cmd[0] == "curl"
        assert "-H" in cmd and "k: v" in cmd  # headers expanded into the command

    @pytest.mark.asyncio
    async def test_download_returns_false_immediately_on_non_retryable_auth_error(self, subject):
        err = subprocess.CalledProcessError(22, ["curl"], stderr="curl: (22) ... 401 Unauthorized")
        with patch("subprocess.run", side_effect=err) as run:
            result = await subject.download("https://x/y", "/tmp/out", {})
        assert result is False
        run.assert_called_once()  # 401 → no retry

    @pytest.mark.asyncio
    async def test_download_retries_then_fails_after_exhausting_attempts(self, subject):
        err = subprocess.CalledProcessError(1, ["curl"], stderr="transient")
        with patch("subprocess.run", side_effect=err) as run, \
                patch("asyncio.sleep", new=AsyncMock()) as sleep:
            result = await subject.download("https://x/y", "/tmp/out", {})
        assert result is False
        assert run.call_count == 2  # max_retries
        sleep.assert_awaited_once()  # one back-off between the two attempts


class TestTarRunner:
    @pytest.fixture
    def subject(self):
        return TarRunner()

    @pytest.mark.asyncio
    async def test_extract_returns_true_on_success(self, subject, tmp_path):
        dest = str(tmp_path / "dest")
        with patch("subprocess.run", return_value=MagicMock()) as run:
            result = await subject.extract("/tmp/a.tgz", dest)
        assert result is True
        cmd = run.call_args[0][0]
        assert cmd[:2] == ["tar", "-xzf"]

    @pytest.mark.asyncio
    async def test_extract_returns_false_when_dest_cannot_be_created(self, subject):
        with patch("os.makedirs", side_effect=OSError("nope")):
            result = await subject.extract("/tmp/a.tgz", "/dest")
        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "stderr",
        ["Unexpected EOF", "No such file or directory", "No space left on device",
         "Permission denied", "some other failure"],
    )
    async def test_extract_returns_false_on_each_tar_error_branch(self, subject, tmp_path, stderr):
        err = subprocess.CalledProcessError(2, ["tar"], stderr=stderr)
        with patch("subprocess.run", side_effect=err):
            result = await subject.extract("/tmp/a.tgz", str(tmp_path / "dest"))
        assert result is False
