import asyncio
import pytest
from unittest.mock import AsyncMock
from pathlib import Path

from worker.services import DownloadService
from worker.runners import CurlRunner, TarRunner
from worker.progress import DownloadProgressTracker


class TestDownloadService:
    @pytest.fixture
    def mock_curl_runner(self):
        runner = AsyncMock(spec=CurlRunner)
        runner.probe_total_size.return_value = None
        return runner

    @pytest.fixture
    def mock_tar_runner(self):
        return AsyncMock(spec=TarRunner)

    @pytest.fixture
    def mock_progress_tracker(self):
        return AsyncMock(spec=DownloadProgressTracker)

    @pytest.fixture
    def subject(self, mock_curl_runner, mock_tar_runner, mock_progress_tracker, tmp_path):
        return DownloadService(
            curl_runner=mock_curl_runner,
            tar_runner=mock_tar_runner,
            progress_tracker=mock_progress_tracker,
            staging_path=str(tmp_path / "staging"),
            download_path=str(tmp_path / "downloads"),
            pictures_path=str(tmp_path / "pictures"),
            videos_path=str(tmp_path / "videos"),
        )

    @pytest.fixture
    def downloads_dir(self, tmp_path):
        d = tmp_path / "downloads"
        d.mkdir()
        return d

    @pytest.fixture
    def staging_dir(self, tmp_path):
        d = tmp_path / "staging"
        d.mkdir()
        return d

    @pytest.mark.asyncio
    async def test_download_chunk_missing_params(self, subject):
        success, message = await subject.download_chunk({"id": 1, "type": "download", "params": {}})

        assert success is False
        assert message == "Missing required download parameters"

    @pytest.mark.asyncio
    async def test_download_chunk_partial_params(self, subject):
        success, message = await subject.download_chunk({
            "id": 1, "type": "download",
            "params": {"chunk_index": 1},
        })

        assert success is False
        assert message == "Missing required download parameters"

    @pytest.mark.asyncio
    async def test_download_chunk_calls_curl_runner(self, subject, mock_curl_runner, staging_dir):
        async def create_file(url, output_path, headers):
            Path(output_path).write_bytes(b"fake content")
            return True

        mock_curl_runner.download.side_effect = create_file

        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "job_id": "test-job-id",
                "user_id": "test-user-id",
                "timestamp": "20240101T120000",
                "auth_user": "0",
                "chunk_index": 1,
                "cookie": "test-cookie",
            },
        }

        success, message = await subject.download_chunk(mock_task)

        mock_curl_runner.download.assert_called_once()
        assert success is True

    @pytest.mark.asyncio
    async def test_download_chunk_downloads_to_staging_path(self, subject, mock_curl_runner, staging_dir):
        async def create_file(url, output_path, headers):
            Path(output_path).write_bytes(b"fake content")
            return True

        mock_curl_runner.download.side_effect = create_file

        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "job_id": "test-job-id",
                "user_id": "test-user-id",
                "timestamp": "20240101T120000",
                "auth_user": "0",
                "chunk_index": 1,
                "cookie": "test-cookie",
            },
        }

        expected_chunk_name = "takeout-20240101T120000Z-1-001.tgz"
        expected_url = (
            f"https://takeout-download.usercontent.google.com/download/{expected_chunk_name}"
            f"?j=test-job-id&i=0&user=test-user-id&authuser=0"
        )
        expected_staging_path = str(staging_dir / expected_chunk_name)

        await subject.download_chunk(mock_task)

        call_args = mock_curl_runner.download.call_args
        assert call_args[0][0] == expected_url
        assert call_args[0][1] == expected_staging_path
        assert "cookie" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_download_chunk_moves_verified_file_to_final_download_path(
        self, subject, mock_curl_runner, downloads_dir, staging_dir
    ):
        async def create_downloaded_file(url, output_path, headers):
            Path(output_path).write_bytes(b"downloaded content")
            return True

        mock_curl_runner.download.side_effect = create_downloaded_file

        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1,
                "job_id": "test-job",
                "user_id": "user-1",
                "timestamp": "20240101T120000",
                "auth_user": "0",
                "cookie": "cookie",
            },
        }

        success, message = await subject.download_chunk(mock_task)

        assert success is True
        assert message == "Download successful"
        final_path = downloads_dir / "takeout-20240101T120000Z-1-001.tgz"
        assert final_path.exists()
        assert final_path.read_bytes() == b"downloaded content"
        assert not (staging_dir / "takeout-20240101T120000Z-1-001.tgz").exists()

    @pytest.mark.asyncio
    async def test_download_chunk_returns_failure_on_empty_file(self, subject, mock_curl_runner, staging_dir):
        async def create_empty_file(url, output_path, headers):
            Path(output_path).write_bytes(b"")
            return True

        mock_curl_runner.download.side_effect = create_empty_file

        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1,
                "job_id": "test",
                "user_id": "user",
                "timestamp": "20240101T120000",
                "auth_user": "0",
                "cookie": "c",
            },
        }

        success, message = await subject.download_chunk(mock_task)

        assert success is False
        assert message == "File not found or empty after download"

    @pytest.mark.asyncio
    async def test_download_chunk_returns_failure_on_corrupted_archive(
        self, subject, mock_curl_runner, mock_tar_runner, staging_dir
    ):
        async def create_file(url, output_path, headers):
            Path(output_path).write_bytes(b"truncated content")
            return True

        mock_curl_runner.download.side_effect = create_file
        mock_tar_runner.verify.return_value = False

        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1,
                "job_id": "test",
                "user_id": "user",
                "timestamp": "20240101T120000",
                "auth_user": "0",
                "cookie": "c",
            },
        }

        success, message = await subject.download_chunk(mock_task)

        assert success is False
        assert message == "Downloaded file failed integrity check (corrupted)"
        mock_tar_runner.verify.assert_called_once_with(
            str(staging_dir / "takeout-20240101T120000Z-1-001.tgz")
        )

    @pytest.mark.asyncio
    async def test_download_chunk_deletes_staging_file_on_corruption(
        self, subject, mock_curl_runner, mock_tar_runner, downloads_dir, staging_dir
    ):
        """A confirmed-corrupt file must not survive to poison a later resume attempt."""
        async def create_file(url, output_path, headers):
            Path(output_path).write_bytes(b"truncated content")
            return True

        mock_curl_runner.download.side_effect = create_file
        mock_tar_runner.verify.return_value = False

        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1,
                "job_id": "test",
                "user_id": "user",
                "timestamp": "20240101T120000",
                "auth_user": "0",
                "cookie": "c",
            },
        }

        await subject.download_chunk(mock_task)

        assert not (staging_dir / "takeout-20240101T120000Z-1-001.tgz").exists()
        assert not (downloads_dir / "takeout-20240101T120000Z-1-001.tgz").exists()

    @pytest.mark.asyncio
    async def test_download_chunk_verifies_archive_before_reporting_success(
        self, subject, mock_curl_runner, mock_tar_runner, staging_dir
    ):
        async def create_file(url, output_path, headers):
            Path(output_path).write_bytes(b"intact content")
            return True

        mock_curl_runner.download.side_effect = create_file
        mock_tar_runner.verify.return_value = True

        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1,
                "job_id": "test",
                "user_id": "user",
                "timestamp": "20240101T120000",
                "auth_user": "0",
                "cookie": "c",
            },
        }

        success, message = await subject.download_chunk(mock_task)

        assert success is True
        assert message == "Download successful"
        mock_tar_runner.verify.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_chunk_probes_total_size_before_downloading(
        self, subject, mock_curl_runner, staging_dir
    ):
        async def create_file(url, output_path, headers):
            Path(output_path).write_bytes(b"content")
            return True

        mock_curl_runner.download.side_effect = create_file
        mock_curl_runner.probe_total_size.return_value = 5000

        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1, "job_id": "test", "user_id": "user",
                "timestamp": "20240101T120000", "auth_user": "0", "cookie": "c",
            },
        }

        await subject.download_chunk(mock_task)

        mock_curl_runner.probe_total_size.assert_called_once()
        probe_call_args = mock_curl_runner.probe_total_size.call_args
        download_call_args = mock_curl_runner.download.call_args
        assert probe_call_args[0][0] == download_call_args[0][0]  # same url

    @pytest.mark.asyncio
    async def test_download_chunk_without_on_progress_does_not_start_tracker(
        self, subject, mock_curl_runner, mock_progress_tracker, staging_dir
    ):
        async def create_file(url, output_path, headers):
            Path(output_path).write_bytes(b"content")
            return True

        mock_curl_runner.download.side_effect = create_file

        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1, "job_id": "test", "user_id": "user",
                "timestamp": "20240101T120000", "auth_user": "0", "cookie": "c",
            },
        }

        await subject.download_chunk(mock_task)

        mock_progress_tracker.track.assert_not_called()

    @pytest.mark.asyncio
    async def test_download_chunk_with_on_progress_tracks_and_stops_after_download(
        self, subject, mock_curl_runner, mock_progress_tracker, staging_dir
    ):
        async def create_file(url, output_path, headers):
            Path(output_path).write_bytes(b"content")
            return True

        mock_curl_runner.download.side_effect = create_file
        mock_curl_runner.probe_total_size.return_value = 5000

        track_call_seen = asyncio.Event()

        async def fake_track(path, total_bytes, on_progress, stop_event):
            track_call_seen.set()
            await stop_event.wait()  # only returns once download_chunk signals completion

        mock_progress_tracker.track.side_effect = fake_track

        on_progress = AsyncMock()
        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1, "job_id": "test", "user_id": "user",
                "timestamp": "20240101T120000", "auth_user": "0", "cookie": "c",
            },
        }

        success, _ = await subject.download_chunk(mock_task, on_progress=on_progress)

        assert success is True
        mock_progress_tracker.track.assert_called_once()
        call_args = mock_progress_tracker.track.call_args[0]
        assert call_args[0] == str(staging_dir / "takeout-20240101T120000Z-1-001.tgz")
        assert call_args[1] == 5000
        assert call_args[2] is on_progress
        assert isinstance(call_args[3], asyncio.Event)

    @pytest.mark.asyncio
    async def test_download_chunk_returns_failure_on_download_failure(self, subject, mock_curl_runner):
        mock_curl_runner.download.return_value = False

        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1,
                "job_id": "test",
                "user_id": "user",
                "timestamp": "20240101T120000",
                "auth_user": "0",
                "cookie": "c",
            },
        }

        success, message = await subject.download_chunk(mock_task)

        assert success is False
        assert message == "Download failed"

    @pytest.mark.asyncio
    async def test_extract_chunk_extracts_and_sorts_files(self, subject, mock_tar_runner, tmp_path):
        downloads_dir = tmp_path / "downloads"
        pictures_dir = tmp_path / "pictures"
        videos_dir = tmp_path / "videos"
        downloads_dir.mkdir()

        tgz_path = downloads_dir / "takeout-20240101T120000Z-1-001.tgz"
        tgz_path.write_bytes(b"fake archive content")

        async def simulate_extraction(archive_path, dest_dir):
            Path(dest_dir).mkdir(parents=True, exist_ok=True)
            (Path(dest_dir) / "photo.jpg").write_bytes(b"jpg data")
            (Path(dest_dir) / "video.mp4").write_bytes(b"mp4 data")
            (Path(dest_dir) / "another.png").write_bytes(b"png data")
            (Path(dest_dir) / "document.pdf").write_bytes(b"pdf data")
            (Path(dest_dir) / "image.jpeg").write_bytes(b"jpeg data")
            (Path(dest_dir) / "movie.mov").write_bytes(b"mov data")
            return True

        mock_tar_runner.extract.side_effect = simulate_extraction

        mock_task = {
            "id": 1,
            "type": "extract",
            "params": {
                "job_id": "test-job-extract",
                "timestamp": "20240101T120000",
                "chunk_index": 1,
            },
        }

        success, message = await subject.extract_chunk(mock_task)

        assert success is True
        assert message == "Extracted 3 pictures and 2 videos"
        assert (pictures_dir / "photo.jpg").exists()
        assert (pictures_dir / "another.png").exists()
        assert (pictures_dir / "image.jpeg").exists()
        assert (videos_dir / "video.mp4").exists()
        assert (videos_dir / "movie.mov").exists()
        assert not (pictures_dir / "document.pdf").exists()
        assert not (videos_dir / "document.pdf").exists()

    @pytest.mark.asyncio
    async def test_extract_chunk_missing_all_params(self, subject):
        success, message = await subject.extract_chunk({"id": 1, "type": "extract", "params": {}})
        assert success is False
        assert message == "Task parameters are missing"

    @pytest.mark.asyncio
    async def test_extract_chunk_missing_required_params(self, subject):
        success, message = await subject.extract_chunk(
            {"id": 1, "type": "extract", "params": {"timestamp": "20240101T120000"}}
        )
        assert success is False
        assert "Missing required parameters for extraction" in message

    @pytest.mark.asyncio
    async def test_extract_chunk_archive_not_found(self, subject):
        success, message = await subject.extract_chunk(
            {"id": 1, "type": "extract",
             "params": {"timestamp": "20240101T120000", "chunk_index": 1}}
        )
        assert success is False
        assert message.startswith("Archive not found:")

    @pytest.mark.asyncio
    async def test_extract_chunk_returns_failure_when_tar_runner_fails(
        self, subject, mock_tar_runner, tmp_path
    ):
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        (downloads_dir / "takeout-20240101T120000Z-1-001.tgz").write_bytes(b"archive")
        mock_tar_runner.extract.return_value = False

        success, message = await subject.extract_chunk(
            {"id": 1, "type": "extract",
             "params": {"timestamp": "20240101T120000", "chunk_index": 1}}
        )
        assert success is False
        assert message == "Failed to extract archive"

    @pytest.mark.asyncio
    async def test_extract_chunk_returns_failure_on_unexpected_exception(
        self, subject, mock_tar_runner, tmp_path
    ):
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()
        (downloads_dir / "takeout-20240101T120000Z-1-001.tgz").write_bytes(b"archive")
        mock_tar_runner.extract.side_effect = RuntimeError("boom")

        success, message = await subject.extract_chunk(
            {"id": 1, "type": "extract",
             "params": {"timestamp": "20240101T120000", "chunk_index": 1}}
        )
        assert success is False
        assert "Extraction error: boom" in message
