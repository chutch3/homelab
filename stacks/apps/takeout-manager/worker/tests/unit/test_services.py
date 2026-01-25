import pytest
from unittest.mock import AsyncMock
from pathlib import Path

from worker.services import DownloadService
from worker.containers import WorkerContainer
from worker.runners import CurlRunner, TarRunner


class TestDownloadService:
    @pytest.fixture
    def container(self):
        """Create a test container."""
        return WorkerContainer()

    @pytest.fixture
    def mock_curl_runner(self):
        """Create a mock CurlRunner."""
        return AsyncMock(spec=CurlRunner)

    @pytest.fixture
    def mock_tar_runner(self):
        """Create a mock TarRunner."""
        return AsyncMock(spec=TarRunner)

    def test_initialization(self, container, mock_curl_runner, mock_tar_runner):
        """Tests that the DownloadService can be initialized."""
        with container.curl_runner.override(mock_curl_runner), \
             container.tar_runner.override(mock_tar_runner):
            subject = container.download_service()
            assert isinstance(subject, DownloadService)

    @pytest.mark.asyncio
    async def test_download_chunk_can_be_called(self, container, mock_curl_runner, mock_tar_runner):
        """An initial 'green' test to ensure the method exists and can be called."""
        mock_task = {
            "id": 1,
            "type": "download",
            "params": {}
        }

        with container.curl_runner.override(mock_curl_runner), \
             container.tar_runner.override(mock_tar_runner):
            subject = container.download_service()
            await subject.download_chunk(mock_task)

    @pytest.mark.asyncio
    async def test_download_chunk_calls_curl_runner(self, container, mock_curl_runner, mock_tar_runner, tmp_path):
        """Tests that download_chunk calls the curl_runner.download() method."""
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()

        # Setup mock behavior to create a real file
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
                "cookie": "test-cookie"
            }
        }

        with container.curl_runner.override(mock_curl_runner), \
             container.tar_runner.override(mock_tar_runner):
            subject = container.download_service()

            # Temporarily patch the DOWNLOAD_PATH constant
            original_download_path = subject.__class__.__module__
            import worker.services
            original_path = worker.services.DOWNLOAD_PATH
            worker.services.DOWNLOAD_PATH = str(download_dir)

            try:
                success, message = await subject.download_chunk(mock_task)
            finally:
                worker.services.DOWNLOAD_PATH = original_path

        mock_curl_runner.download.assert_called_once()
        assert success is True

    @pytest.mark.asyncio
    async def test_download_chunk_constructs_correct_curl_command(self, container, mock_curl_runner, mock_tar_runner, tmp_path):
        """Tests that download_chunk calls download() with correct parameters."""
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()

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
                "cookie": "test-cookie"
            }
        }

        expected_chunk_name = "takeout-20240101T120000Z-001.tgz"
        expected_url = f"https://takeout-download.usercontent.google.com/download/{expected_chunk_name}?j=test-job-id&i=0&user=test-user-id&authuser=0"
        expected_output_path = str(download_dir / expected_chunk_name)

        with container.curl_runner.override(mock_curl_runner), \
             container.tar_runner.override(mock_tar_runner):
            subject = container.download_service()

            import worker.services
            original_path = worker.services.DOWNLOAD_PATH
            worker.services.DOWNLOAD_PATH = str(download_dir)

            try:
                await subject.download_chunk(mock_task)
            finally:
                worker.services.DOWNLOAD_PATH = original_path

        # Verify download() was called with correct parameters
        mock_curl_runner.download.assert_called_once()
        call_args = mock_curl_runner.download.call_args
        assert call_args[0][0] == expected_url  # URL
        assert call_args[0][1] == expected_output_path  # output_path
        assert 'cookie' in call_args[0][2]  # headers dict

    @pytest.mark.asyncio
    async def test_download_chunk_returns_success_on_file_creation(self, container, mock_curl_runner, mock_tar_runner, tmp_path):
        """Tests that download_chunk returns success when the file is created."""
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()

        # Simulate successful download by creating a real file
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
                "cookie": "cookie"
            }
        }

        with container.curl_runner.override(mock_curl_runner), \
             container.tar_runner.override(mock_tar_runner):
            subject = container.download_service()

            import worker.services
            original_path = worker.services.DOWNLOAD_PATH
            worker.services.DOWNLOAD_PATH = str(download_dir)

            try:
                success, message = await subject.download_chunk(mock_task)
            finally:
                worker.services.DOWNLOAD_PATH = original_path

        assert success is True
        assert message == "Download successful"

    @pytest.mark.asyncio
    async def test_download_chunk_returns_failure_on_empty_file(self, container, mock_curl_runner, mock_tar_runner, tmp_path):
        """Tests that download_chunk returns failure if the downloaded file is empty."""
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()

        # Create an empty file
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
                "cookie": "c"
            }
        }

        with container.curl_runner.override(mock_curl_runner), \
             container.tar_runner.override(mock_tar_runner):
            subject = container.download_service()

            import worker.services
            original_path = worker.services.DOWNLOAD_PATH
            worker.services.DOWNLOAD_PATH = str(download_dir)

            try:
                success, message = await subject.download_chunk(mock_task)
            finally:
                worker.services.DOWNLOAD_PATH = original_path

        assert success is False
        assert message == "File not found or empty after download"

    @pytest.mark.asyncio
    async def test_download_chunk_returns_failure_on_download_failure(self, container, mock_curl_runner, mock_tar_runner):
        """Tests that download_chunk returns failure when download() fails."""
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
                "cookie": "c"
            }
        }

        with container.curl_runner.override(mock_curl_runner), \
             container.tar_runner.override(mock_tar_runner):
            subject = container.download_service()
            success, message = await subject.download_chunk(mock_task)

        assert success is False
        assert message == "Download failed"

    @pytest.mark.asyncio
    async def test_extract_chunk_extracts_and_sorts_files(self, container, mock_curl_runner, mock_tar_runner, tmp_path):
        """Tests that extract_chunk correctly extracts files and sorts them into
        pictures and videos directories using real filesystem operations."""

        # Setup real directories
        downloads_dir = tmp_path / "downloads"
        pictures_dir = tmp_path / "pictures"
        videos_dir = tmp_path / "videos"
        downloads_dir.mkdir()

        # Create a real archive file
        tgz_path = downloads_dir / "takeout-20240101T120000Z-001.tgz"
        tgz_path.write_bytes(b"fake archive content")

        # Mock tar_runner.extract to simulate extraction by creating real files
        async def simulate_extraction(archive_path, dest_dir):
            # Create real extracted files in the temp directory
            Path(dest_dir).mkdir(parents=True, exist_ok=True)
            (Path(dest_dir) / "photo.jpg").write_bytes(b"jpg data")
            (Path(dest_dir) / "video.mp4").write_bytes(b"mp4 data")
            (Path(dest_dir) / "another.png").write_bytes(b"png data")
            (Path(dest_dir) / "document.pdf").write_bytes(b"pdf data")
            (Path(dest_dir) / "image.jpeg").write_bytes(b"jpeg data")
            (Path(dest_dir) / "movie.mov").write_bytes(b"mov data")
            return True

        mock_tar_runner.extract.side_effect = simulate_extraction

        # Simulate a downloaded chunk task
        mock_task = {
            "id": 1,
            "type": "extract",
            "params": {
                "job_id": "test-job-extract",
                "timestamp": "20240101T120000",
                "chunk_index": 1,
            }
        }

        with container.curl_runner.override(mock_curl_runner), \
             container.tar_runner.override(mock_tar_runner):
            subject = container.download_service()

            import worker.services
            original_download = worker.services.DOWNLOAD_PATH
            original_pictures = worker.services.PICTURES_PATH
            original_videos = worker.services.VIDEOS_PATH
            worker.services.DOWNLOAD_PATH = str(downloads_dir)
            worker.services.PICTURES_PATH = str(pictures_dir)
            worker.services.VIDEOS_PATH = str(videos_dir)

            try:
                success, message = await subject.extract_chunk(mock_task)
            finally:
                worker.services.DOWNLOAD_PATH = original_download
                worker.services.PICTURES_PATH = original_pictures
                worker.services.VIDEOS_PATH = original_videos

        # Assertions - check real files were moved
        assert success is True
        assert message == "Extracted 3 pictures and 2 videos"

        # Verify pictures were moved
        assert (pictures_dir / "photo.jpg").exists()
        assert (pictures_dir / "another.png").exists()
        assert (pictures_dir / "image.jpeg").exists()

        # Verify videos were moved
        assert (videos_dir / "video.mp4").exists()
        assert (videos_dir / "movie.mov").exists()

        # Verify PDF was NOT moved
        assert not (pictures_dir / "document.pdf").exists()
        assert not (videos_dir / "document.pdf").exists()
