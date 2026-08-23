import pytest
from unittest.mock import AsyncMock, Mock
import asyncio

from worker.daemon import run_daemon
from worker.containers import WorkerContainer
from worker.manager_client import ManagerClient
from worker.services import DownloadService, MetadataService, TimelineService


class TestRunDaemon:
    @pytest.fixture
    async def container(self):
        container = WorkerContainer()
        container.config.manager_url.from_value("http://test-manager:8000")
        container.config.log.level.from_value("ERROR")
        container.config.paths.staging.from_value("/tmp/staging")
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

        mock_download_service.download_chunk.assert_called_once()
        call_args = mock_download_service.download_chunk.call_args
        assert call_args.args[0] == mock_task
        assert callable(call_args.kwargs["on_progress"])
        mock_manager_client.report_task_status.assert_called_once_with(
            1, "downloaded", "Download successful"
        )

    @pytest.mark.asyncio
    async def test_daemon_processes_extract_task(self, container):
        # 'extract' is now the whole-export GPTH pass, handled by MetadataService.
        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_task = {
            "id": 9,
            "type": "extract",
            "params": {"job_id": "test-job", "timestamp": "20240101T120000", "total_chunks": 1},
        }
        mock_manager_client.get_next_task.side_effect = [mock_task, None]

        mock_metadata_service = Mock(spec=MetadataService)
        mock_metadata_service.process_job_metadata.return_value = (
            True, "Extracted 100 files", {"takeout-20240101T120000Z-1-001.tgz": {"2024-01": 100}}
        )

        with container.manager_client.override(mock_manager_client), \
             container.metadata_service.override(mock_metadata_service):
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        mock_metadata_service.process_job_metadata.assert_called_once_with(mock_task)
        mock_manager_client.report_metadata_task_status.assert_called_once_with(
            9, "completed", "Extracted 100 files"
        )
        # The piggyback timeline is reported too.
        mock_manager_client.report_timeline.assert_called_once_with(
            "takeout-20240101T120000Z-1-001.tgz", {"2024-01": 100}
        )
        mock_manager_client.report_task_status.assert_not_called()

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
    @pytest.mark.asyncio
    async def test_daemon_processes_extract_archive_task(self, container):
        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_task = {
            "id": 7,
            "type": "extract_archive",
            "params": {"filename": "takeout-Z-001.tgz"},
        }
        mock_manager_client.get_next_task.side_effect = [mock_task, None]

        mock_metadata_service = Mock(spec=MetadataService)
        mock_metadata_service.extract_single_archive.return_value = (
            True, "Extracted 3 pictures and 1 videos", {"takeout-Z-001.tgz": {"2019-07": 4}}
        )

        with container.manager_client.override(mock_manager_client), \
             container.metadata_service.override(mock_metadata_service):
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        mock_metadata_service.extract_single_archive.assert_called_once_with(mock_task)
        mock_manager_client.report_archive_extraction_status.assert_called_once_with(
            7, "extracted", "Extracted 3 pictures and 1 videos"
        )
        mock_manager_client.report_timeline.assert_called_once_with(
            "takeout-Z-001.tgz", {"2019-07": 4}
        )
        mock_manager_client.report_task_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_daemon_processes_timeline_task(self, container):
        mock_manager_client = AsyncMock(spec=ManagerClient)
        mock_task = {"id": 4, "type": "timeline", "params": {"filename": "takeout-Z-001.tgz"}}
        mock_manager_client.get_next_task.side_effect = [mock_task, None]

        mock_timeline_service = Mock(spec=TimelineService)
        mock_timeline_service.build_timeline.return_value = (
            True, {"2019-07": 10}, "10 dated media across 1 months"
        )

        with container.manager_client.override(mock_manager_client), \
             container.timeline_service.override(mock_timeline_service):
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        mock_timeline_service.build_timeline.assert_called_once_with(mock_task)
        mock_manager_client.report_timeline.assert_called_once_with(
            "takeout-Z-001.tgz", {"2019-07": 10}
        )
        mock_manager_client.report_task_status.assert_not_called()

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
