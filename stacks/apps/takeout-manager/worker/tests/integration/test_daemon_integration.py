"""Integration tests for the daemon dispatch-to-service pipeline.

These tests wire a real DownloadService (with injected paths) to the daemon
via the container, mocking only the external boundaries: the manager HTTP client
and the subprocess runners (curl/tar). This validates that the daemon correctly
dispatches tasks and that the service correctly constructs paths and file operations.
"""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from worker.containers import WorkerContainer
from worker.daemon import run_daemon
from worker.manager_client import ManagerClient
from worker.runners import CurlRunner, TarRunner
from worker.services import DownloadService


class TestDaemonIntegration:
    @pytest.fixture
    async def worker_container(self, tmp_path):
        container = WorkerContainer()
        container.config.manager_url.from_value("http://fake-manager")
        container.config.log.level.from_value("ERROR")
        container.config.paths.downloads.from_value(str(tmp_path / "downloads"))
        container.config.paths.pictures.from_value(str(tmp_path / "pictures"))
        container.config.paths.videos.from_value(str(tmp_path / "videos"))
        await container.init_resources()
        container.wire(modules=["worker.daemon"])
        yield container
        await container.shutdown_resources()

    @pytest.mark.asyncio
    async def test_full_download_cycle(self, worker_container, tmp_path):
        """Daemon dispatches a download task through the real service and reports success."""
        downloads_dir = tmp_path / "downloads"
        downloads_dir.mkdir()

        download_task = {
            "id": 1,
            "type": "download",
            "params": {
                "job_id": "test-job",
                "user_id": "user-1",
                "timestamp": "20240101T120000",
                "auth_user": "0",
                "chunk_index": 1,
                "cookie": "session=abc123",
            },
        }

        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_manager_client.get_next_task.side_effect = [download_task, None]

        mock_curl_runner = AsyncMock(spec=CurlRunner)

        async def simulate_download(url, output_path, headers):
            Path(output_path).write_bytes(b"fake archive")
            return True

        mock_curl_runner.download.side_effect = simulate_download

        service = DownloadService(
            curl_runner=mock_curl_runner,
            tar_runner=AsyncMock(spec=TarRunner),
            download_path=str(downloads_dir),
            pictures_path=str(tmp_path / "pictures"),
            videos_path=str(tmp_path / "videos"),
        )

        with worker_container.manager_client.override(mock_manager_client), \
             worker_container.download_service.override(service):
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        mock_manager_client.report_task_status.assert_called_once_with(
            1, "downloaded", "Download successful"
        )
        assert (downloads_dir / "takeout-20240101T120000Z-001.tgz").exists()

    @pytest.mark.asyncio
    async def test_full_extract_cycle(self, worker_container, tmp_path):
        """Daemon dispatches an extract task through the real service and reports success."""
        downloads_dir = tmp_path / "downloads"
        pictures_dir = tmp_path / "pictures"
        videos_dir = tmp_path / "videos"
        downloads_dir.mkdir()
        (downloads_dir / "takeout-20240101T120000Z-001.tgz").write_bytes(b"fake archive")

        extract_task = {
            "id": 2,
            "type": "extract",
            "params": {
                "job_id": "test-job",
                "timestamp": "20240101T120000",
                "chunk_index": 1,
            },
        }

        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_manager_client.get_next_task.side_effect = [extract_task, None]

        mock_tar_runner = AsyncMock(spec=TarRunner)

        async def simulate_extract(archive_path, dest_dir):
            Path(dest_dir).mkdir(parents=True, exist_ok=True)
            (Path(dest_dir) / "photo.jpg").write_bytes(b"jpg")
            (Path(dest_dir) / "clip.mp4").write_bytes(b"mp4")
            return True

        mock_tar_runner.extract.side_effect = simulate_extract

        service = DownloadService(
            curl_runner=AsyncMock(spec=CurlRunner),
            tar_runner=mock_tar_runner,
            download_path=str(downloads_dir),
            pictures_path=str(pictures_dir),
            videos_path=str(videos_dir),
        )

        with worker_container.manager_client.override(mock_manager_client), \
             worker_container.download_service.override(service):
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        mock_manager_client.report_task_status.assert_called_once_with(
            2, "extracted", "Extracted 1 pictures and 1 videos"
        )
        assert (pictures_dir / "photo.jpg").exists()
        assert (videos_dir / "clip.mp4").exists()

    @pytest.mark.asyncio
    async def test_download_failure_reports_failed_status(self, worker_container, tmp_path):
        """Daemon reports failed status when the runner returns False."""
        download_task = {
            "id": 3,
            "type": "download",
            "params": {
                "job_id": "test-job",
                "user_id": "user-1",
                "timestamp": "20240101T120000",
                "auth_user": "0",
                "chunk_index": 1,
                "cookie": "session=abc",
            },
        }

        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_manager_client.get_next_task.side_effect = [download_task, None]

        mock_curl_runner = AsyncMock(spec=CurlRunner)
        mock_curl_runner.download.return_value = False

        service = DownloadService(
            curl_runner=mock_curl_runner,
            tar_runner=AsyncMock(spec=TarRunner),
            download_path=str(tmp_path / "downloads"),
            pictures_path=str(tmp_path / "pictures"),
            videos_path=str(tmp_path / "videos"),
        )

        with worker_container.manager_client.override(mock_manager_client), \
             worker_container.download_service.override(service):
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        mock_manager_client.report_task_status.assert_called_once_with(
            3, "failed", "Download failed"
        )
