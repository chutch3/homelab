"""Unit tests for the subprocess adapter runners (CurlRunner, TarRunner).

These classes are the owned abstraction over the curl/tar subprocesses, so the
subprocess boundary is patched here at the adapter — the one place mocking a
system dep directly is appropriate. asyncio.sleep is patched to keep the retry
test fast.
"""

import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.runners import CurlRunner, TarRunner, GpthRunner


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

    @pytest.mark.asyncio
    async def test_probe_total_size_returns_total_from_content_range_header(self, subject):
        headers = "HTTP/2 206\r\ncontent-range: bytes 0-0/53053312630\r\n\r\n"
        with patch("subprocess.run", return_value=MagicMock(stdout=headers)) as run:
            total = await subject.probe_total_size("https://x/y", {"cookie": "c"})
        assert total == 53053312630
        cmd = run.call_args[0][0]
        assert cmd[0] == "curl"
        assert "-r" in cmd and "0-0" in cmd
        assert "-D" in cmd  # dump headers so we can read Content-Range

    @pytest.mark.asyncio
    async def test_probe_total_size_returns_none_when_header_missing(self, subject):
        headers = "HTTP/2 200\r\ncontent-type: text/html\r\n\r\n"
        with patch("subprocess.run", return_value=MagicMock(stdout=headers)):
            total = await subject.probe_total_size("https://x/y", {})
        assert total is None

    @pytest.mark.asyncio
    async def test_probe_total_size_returns_none_on_curl_error(self, subject):
        err = subprocess.CalledProcessError(22, ["curl"], stderr="error")
        with patch("subprocess.run", side_effect=err):
            total = await subject.probe_total_size("https://x/y", {})
        assert total is None


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

    @pytest.mark.asyncio
    async def test_verify_returns_true_for_intact_archive(self, subject):
        with patch("subprocess.run", return_value=MagicMock()) as run:
            result = await subject.verify("/tmp/a.tgz")
        assert result is True
        cmd = run.call_args[0][0]
        assert cmd == ["tar", "-tzf", "/tmp/a.tgz"]

    @pytest.mark.asyncio
    async def test_verify_returns_false_for_corrupted_archive(self, subject):
        err = subprocess.CalledProcessError(2, ["tar"], stderr="Unexpected EOF in archive")
        with patch("subprocess.run", side_effect=err):
            result = await subject.verify("/tmp/a.tgz")
        assert result is False


class TestGpthRunner:
    @pytest.fixture
    def subject(self):
        return GpthRunner()

    @pytest.mark.asyncio
    async def test_process_returns_true_on_success(self, subject):
        with patch("subprocess.run", return_value=MagicMock()) as run:
            result = await subject.process("/tmp/raw", "/tmp/out")
        assert result is True
        cmd = run.call_args[0][0]
        assert cmd[0] == "gpth"
        assert "--input" in cmd and "/tmp/raw" in cmd
        assert "--output" in cmd and "/tmp/out" in cmd
        # No ALL_PHOTOS wrapper folder — pictures_path/videos_path are already
        # dedicated destinations, so output should be flat year/month dirs.
        all_photos_flag_index = cmd.index("--all-photos-dir")
        assert cmd[all_photos_flag_index + 1] == ""
        # "nothing" mode: no album symlinks/duplicates for MetadataService's
        # extension-based walk to double-count, and no data loss (unlike "ignore").
        albums_flag_index = cmd.index("--albums")
        assert cmd[albums_flag_index + 1] == "nothing"
        assert "--no-interactive" in cmd
        # Pinned to DEVNULL: an unredirected stdin was observed to hang the
        # real binary indefinitely even with --no-interactive omitted from
        # consideration entirely — belt and suspenders against a stuck worker.
        assert run.call_args.kwargs["stdin"] == subprocess.DEVNULL

    @pytest.mark.asyncio
    async def test_process_returns_false_and_logs_stderr_on_failure(self, subject, caplog):
        err = subprocess.CalledProcessError(1, ["gpth"], stderr="gpth: no media files found")
        with patch("subprocess.run", side_effect=err):
            result = await subject.process("/tmp/raw", "/tmp/out")
        assert result is False
        assert "no media files found" in caplog.text
