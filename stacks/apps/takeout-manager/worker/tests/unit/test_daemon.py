import pytest
from unittest.mock import AsyncMock, Mock
import asyncio

from worker.daemon import run_daemon
from worker.containers import WorkerContainer
from worker.manager_client import ManagerClient
from worker.services import DownloadService


class TestRunDaemon:
    @pytest.fixture
    async def container(self):
        container = WorkerContainer()
        container.config.manager_url.from_value("http://test-manager:8000")
        container.config.log.level.from_value("ERROR")
        container.config.paths.downloads.from_value("/tmp/downloads")
        container.config.paths.pictures.from_value("/tmp/pictures")
        container.config.paths.videos.from_value("/tmp/videos")
        await container.init_resources()
        container.wire(modules=["worker.daemon"])
        yield container
        await container.shutdown_resources()

    @pytest.mark.asyncio
    async def test_daemon_processes_download_task(self, container):
        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1,
                "timestamp": "20240101T120000",
                "job_id": "test-job",
                "user_id": "test-user",
                "auth_user": "0",
                "cookie": "test-cookie",
            },
        }
        mock_manager_client.get_next_task.side_effect = [mock_task, None]

        mock_download_service = Mock(spec=DownloadService)
        mock_download_service.download_chunk.return_value = (True, "Download successful")

        with container.manager_client.override(mock_manager_client), \
             container.download_service.override(mock_download_service):
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        mock_download_service.download_chunk.assert_called_once_with(mock_task)
        mock_manager_client.report_task_status.assert_called_once_with(
            1, "downloaded", "Download successful"
        )

    @pytest.mark.asyncio
    async def test_daemon_processes_extract_task(self, container):
        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_task = {
            "id": 2,
            "type": "extract",
            "params": {
                "chunk_index": 1,
                "timestamp": "20240101T120000",
                "job_id": "test-job",
            },
        }
        mock_manager_client.get_next_task.side_effect = [mock_task, None]

        mock_download_service = Mock(spec=DownloadService)
        mock_download_service.extract_chunk.return_value = (True, "Extracted 10 pictures and 5 videos")

        with container.manager_client.override(mock_manager_client), \
             container.download_service.override(mock_download_service):
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        mock_download_service.extract_chunk.assert_called_once_with(mock_task)
        mock_manager_client.report_task_status.assert_called_once_with(
            2, "extracted", "Extracted 10 pictures and 5 videos"
        )

    @pytest.mark.asyncio
    async def test_daemon_handles_failed_download(self, container):
        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_task = {"id": 3, "type": "download", "params": {"chunk_index": 1}}
        mock_manager_client.get_next_task.side_effect = [mock_task, None]

        mock_download_service = Mock(spec=DownloadService)
        mock_download_service.download_chunk.return_value = (False, "Download failed")

        with container.manager_client.override(mock_manager_client), \
             container.download_service.override(mock_download_service):
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        mock_manager_client.report_task_status.assert_called_once_with(
            3, "failed", "Download failed"
        )

    @pytest.mark.asyncio
    async def test_daemon_handles_unknown_task_type(self, container):
        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_task = {"id": 4, "type": "unknown_type", "params": {}}
        mock_manager_client.get_next_task.side_effect = [mock_task, None]

        mock_download_service = Mock(spec=DownloadService)

        with container.manager_client.override(mock_manager_client), \
             container.download_service.override(mock_download_service):
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        mock_manager_client.report_task_status.assert_called_once_with(
            4, "failed", "Unknown task type: unknown_type"
        )

    @pytest.mark.asyncio
    async def test_daemon_does_not_report_status_when_no_tasks(self, container):
        """Daemon polls but never reports status when there are no tasks."""
        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_manager_client.get_next_task.return_value = None

        with container.manager_client.override(mock_manager_client):
            try:
                await asyncio.wait_for(run_daemon(), timeout=0.2)
            except asyncio.TimeoutError:
                pass

        mock_manager_client.get_next_task.assert_called()
        mock_manager_client.report_task_status.assert_not_called()
