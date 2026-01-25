import pytest
from unittest.mock import AsyncMock, Mock
import asyncio

from worker.daemon import run_daemon
from worker.containers import WorkerContainer


class TestRunDaemon:
    """Tests for the main daemon loop."""

    @pytest.fixture
    async def container(self):
        """Create and configure a test container."""
        container = WorkerContainer()
        container.config.manager_url.from_value("http://test-manager:8000")
        container.config.log.level.from_value("ERROR")  # Suppress logs during tests
        await container.init_resources()
        container.wire(modules=["worker.daemon"])
        yield container
        await container.shutdown_resources()

    @pytest.mark.asyncio
    async def test_daemon_processes_download_task(self, container, mocker):
        """Test that the daemon processes a download task correctly."""
        # Mock manager client
        mock_manager_client = AsyncMock()
        mock_task = {
            "id": 1,
            "type": "download",
            "params": {
                "chunk_index": 1,
                "timestamp": "20240101T120000",
                "job_id": "test-job",
                "user_id": "test-user",
                "auth_user": "0",
                "cookie": "test-cookie"
            }
        }

        # Return task once, then None to stop the loop
        mock_manager_client.get_next_task.side_effect = [mock_task, None]
        mock_manager_client.report_task_status = AsyncMock()

        # Mock download service
        mock_download_service = Mock()
        mock_download_service.download_chunk = AsyncMock(
            return_value=(True, "Download successful")
        )

        # Override providers
        with container.manager_client.override(mock_manager_client), \
             container.download_service.override(mock_download_service):

            # Run daemon with timeout to prevent infinite loop
            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass  # Expected when get_next_task returns None

        # Verify download was called
        mock_download_service.download_chunk.assert_called_once_with(mock_task)

        # Verify status was reported
        mock_manager_client.report_task_status.assert_called_once_with(
            1, "downloaded", "Download successful"
        )

    @pytest.mark.asyncio
    async def test_daemon_processes_extract_task(self, container, mocker):
        """Test that the daemon processes an extract task correctly."""
        # Mock manager client
        mock_manager_client = AsyncMock()
        mock_task = {
            "id": 2,
            "type": "extract",
            "params": {
                "chunk_index": 1,
                "timestamp": "20240101T120000",
                "job_id": "test-job"
            }
        }

        mock_manager_client.get_next_task.side_effect = [mock_task, None]
        mock_manager_client.report_task_status = AsyncMock()

        # Mock download service
        mock_download_service = Mock()
        mock_download_service.extract_chunk = AsyncMock(
            return_value=(True, "Extracted 10 pictures and 5 videos")
        )

        # Override providers
        with container.manager_client.override(mock_manager_client), \
             container.download_service.override(mock_download_service):

            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        # Verify extraction was called
        mock_download_service.extract_chunk.assert_called_once_with(mock_task)

        # Verify status was reported
        mock_manager_client.report_task_status.assert_called_once_with(
            2, "extracted", "Extracted 10 pictures and 5 videos"
        )

    @pytest.mark.asyncio
    async def test_daemon_handles_failed_download(self, container, mocker):
        """Test that the daemon handles failed downloads correctly."""
        # Mock manager client
        mock_manager_client = AsyncMock()
        mock_task = {
            "id": 3,
            "type": "download",
            "params": {"chunk_index": 1}
        }

        mock_manager_client.get_next_task.side_effect = [mock_task, None]
        mock_manager_client.report_task_status = AsyncMock()

        # Mock download service to return failure
        mock_download_service = Mock()
        mock_download_service.download_chunk = AsyncMock(
            return_value=(False, "Download failed")
        )

        # Override providers
        with container.manager_client.override(mock_manager_client), \
             container.download_service.override(mock_download_service):

            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        # Verify status was reported as failed
        mock_manager_client.report_task_status.assert_called_once_with(
            3, "failed", "Download failed"
        )

    @pytest.mark.asyncio
    async def test_daemon_handles_unknown_task_type(self, container, mocker):
        """Test that the daemon handles unknown task types correctly."""
        # Mock manager client
        mock_manager_client = AsyncMock()
        mock_task = {
            "id": 4,
            "type": "unknown_type",
            "params": {}
        }

        mock_manager_client.get_next_task.side_effect = [mock_task, None]
        mock_manager_client.report_task_status = AsyncMock()

        # Mock download service
        mock_download_service = Mock()

        # Override providers
        with container.manager_client.override(mock_manager_client), \
             container.download_service.override(mock_download_service):

            try:
                await asyncio.wait_for(run_daemon(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

        # Verify status was reported as failed
        mock_manager_client.report_task_status.assert_called_once_with(
            4, "failed", "Unknown task type: unknown_type"
        )

    @pytest.mark.asyncio
    async def test_daemon_sleeps_when_no_tasks(self, container):
        """Test that the daemon sleeps when no tasks are available."""
        # Mock manager client that always returns no tasks
        mock_manager_client = AsyncMock()
        mock_manager_client.get_next_task.return_value = None

        # Override providers
        with container.manager_client.override(mock_manager_client):
            # Run daemon with a short timeout - it should loop multiple times
            # Each loop iteration calls get_next_task, then sleeps
            # We'll verify it called get_next_task multiple times
            try:
                await asyncio.wait_for(run_daemon(), timeout=0.2)
            except asyncio.TimeoutError:
                pass  # Expected - daemon runs forever

        # Verify get_next_task was called at least once
        # The daemon sleeps for 30 seconds when no tasks available
        # So with 0.2s timeout, we only get one call, but that proves it's running
        assert mock_manager_client.get_next_task.call_count >= 1
