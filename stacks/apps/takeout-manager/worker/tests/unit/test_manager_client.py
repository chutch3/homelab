import pytest
from unittest.mock import AsyncMock, Mock
import httpx

from worker.manager_client import ManagerClient, init_async_client


class TestInitAsyncClient:
    """Tests for the async client resource initialization."""

    @pytest.mark.asyncio
    async def test_init_async_client_yields_client(self):
        """Test that init_async_client yields an AsyncClient with the correct base_url."""
        manager_url = "http://localhost:8000"

        async for client in init_async_client(manager_url):
            assert isinstance(client, httpx.AsyncClient)
            assert str(client.base_url).rstrip('/') == manager_url


class TestManagerClient:
    """Tests for ManagerClient."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock AsyncClient."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def subject(self, mock_client):
        """Create a ManagerClient instance with mock client."""
        return ManagerClient(client=mock_client)

    @pytest.mark.asyncio
    async def test_get_next_task_returns_task(self, subject, mock_client):
        """Test that get_next_task returns a task when available."""
        expected_task = {
            "id": 1,
            "type": "download",
            "params": {"chunk_index": 1}
        }

        mock_response = Mock()
        mock_response.json.return_value = expected_task
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        task = await subject.get_next_task()

        assert task == expected_task
        mock_client.get.assert_called_once_with("/api/tasks/next")

    @pytest.mark.asyncio
    async def test_get_next_task_returns_none_when_no_task(self, subject, mock_client):
        """Test that get_next_task returns None when no task is available."""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        task = await subject.get_next_task()

        assert task is None

    @pytest.mark.asyncio
    async def test_get_next_task_returns_none_when_task_has_no_id(self, subject, mock_client):
        """Test that get_next_task returns None when task has no id."""
        mock_response = Mock()
        mock_response.json.return_value = {"type": "download"}
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        task = await subject.get_next_task()

        assert task is None

    @pytest.mark.asyncio
    async def test_get_next_task_handles_connection_error(self, subject, mock_client):
        """Test that get_next_task handles connection errors gracefully."""
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        task = await subject.get_next_task()

        assert task is None

    @pytest.mark.asyncio
    async def test_get_next_task_handles_timeout(self, subject, mock_client):
        """Test that get_next_task handles timeout errors."""
        mock_client.get.side_effect = httpx.TimeoutException("Request timeout")

        task = await subject.get_next_task()

        assert task is None

    @pytest.mark.asyncio
    async def test_report_task_status_sends_correct_payload(self, subject, mock_client):
        """Test that report_task_status sends the correct status update."""
        mock_response = Mock()
        mock_client.post.return_value = mock_response

        await subject.report_task_status(
            task_id=123,
            status="downloaded",
            message="Download successful"
        )

        mock_client.post.assert_called_once_with(
            "/api/tasks/123/status",
            json={"status": "downloaded", "message": "Download successful"}
        )

    @pytest.mark.asyncio
    async def test_report_task_status_handles_connection_error(self, subject, mock_client):
        """Test that report_task_status handles connection errors gracefully."""
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        # Should not raise an exception
        await subject.report_task_status(123, "failed", "Error")

        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_report_task_status_with_empty_message(self, subject, mock_client):
        """Test that report_task_status works with empty message."""
        mock_response = Mock()
        mock_client.post.return_value = mock_response

        await subject.report_task_status(task_id=456, status="extracted")

        mock_client.post.assert_called_once_with(
            "/api/tasks/456/status",
            json={"status": "extracted", "message": ""}
        )
