import pytest
from unittest.mock import AsyncMock
from pathlib import Path

from worker.services import DownloadService
from worker.runners import CurlRunner, TarRunner


class TestDownloadService:
    @pytest.fixture
    def mock_curl_runner(self):
        return AsyncMock(spec=CurlRunner)

    @pytest.fixture
    def mock_tar_runner(self):
        return AsyncMock(spec=TarRunner)

    @pytest.fixture
    def subject(self, mock_curl_runner, mock_tar_runner, tmp_path):
        return DownloadService(
            curl_runner=mock_curl_runner,
            tar_runner=mock_tar_runner,
            download_path=str(tmp_path / "downloads"),
            pictures_path=str(tmp_path / "pictures"),
            videos_path=str(tmp_path / "videos"),
        )

    @pytest.fixture
    def downloads_dir(self, tmp_path):
        d = tmp_path / "downloads"
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
    async def test_download_chunk_calls_curl_runner(self, subject, mock_curl_runner, downloads_dir):
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
    async def test_download_chunk_constructs_correct_url(self, subject, mock_curl_runner, downloads_dir):
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

        expected_chunk_name = "takeout-20240101T120000Z-001.tgz"
        expected_url = (
            f"https://takeout-download.usercontent.google.com/download/{expected_chunk_name}"
            f"?j=test-job-id&i=0&user=test-user-id&authuser=0"
        )
        expected_output_path = str(downloads_dir / expected_chunk_name)

        await subject.download_chunk(mock_task)

        call_args = mock_curl_runner.download.call_args
        assert call_args[0][0] == expected_url
        assert call_args[0][1] == expected_output_path
        assert "cookie" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_download_chunk_returns_success_on_file_creation(self, subject, mock_curl_runner, downloads_dir):
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

    @pytest.mark.asyncio
    async def test_download_chunk_returns_failure_on_empty_file(self, subject, mock_curl_runner, downloads_dir):
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

        tgz_path = downloads_dir / "takeout-20240101T120000Z-001.tgz"
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
        (downloads_dir / "takeout-20240101T120000Z-001.tgz").write_bytes(b"archive")
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
        (downloads_dir / "takeout-20240101T120000Z-001.tgz").write_bytes(b"archive")
        mock_tar_runner.extract.side_effect = RuntimeError("boom")

        success, message = await subject.extract_chunk(
            {"id": 1, "type": "extract",
             "params": {"timestamp": "20240101T120000", "chunk_index": 1}}
        )
        assert success is False
        assert "Extraction error: boom" in message
