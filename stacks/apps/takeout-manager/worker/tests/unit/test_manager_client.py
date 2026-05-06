import pytest
from unittest.mock import AsyncMock, Mock
import httpx

from worker.manager_client import ManagerClient, init_async_client


@pytest.mark.asyncio
async def test_init_async_client_yields_client():
    manager_url = "http://localhost:8000"

    async for client in init_async_client(manager_url):
        assert isinstance(client, httpx.AsyncClient)
        assert str(client.base_url).rstrip('/') == manager_url


class TestManagerClient:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def subject(self, mock_client):
        return ManagerClient(client=mock_client)

    @pytest.mark.asyncio
    async def test_get_next_task_returns_task(self, subject, mock_client):
        expected_task = {
            "id": 1,
            "type": "download",
            "params": {"chunk_index": 1}
        }

        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = expected_task
        mock_client.get.return_value = mock_response

        task = await subject.get_next_task()

        assert task == expected_task
        mock_client.get.assert_called_once_with("/api/tasks/next")

    @pytest.mark.asyncio
    async def test_get_next_task_returns_none_when_no_task(self, subject, mock_client):
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {}
        mock_client.get.return_value = mock_response

        task = await subject.get_next_task()

        assert task is None

    @pytest.mark.asyncio
    async def test_get_next_task_returns_none_when_task_has_no_id(self, subject, mock_client):
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"type": "download"}
        mock_client.get.return_value = mock_response

        task = await subject.get_next_task()

        assert task is None

    @pytest.mark.asyncio
    async def test_get_next_task_handles_connection_error(self, subject, mock_client):
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        task = await subject.get_next_task()

        assert task is None

    @pytest.mark.asyncio
    async def test_get_next_task_handles_timeout(self, subject, mock_client):
        mock_client.get.side_effect = httpx.TimeoutException("Request timeout")

        task = await subject.get_next_task()

        assert task is None

    @pytest.mark.asyncio
    async def test_report_task_status_sends_correct_payload(self, subject, mock_client):
        mock_response = Mock(spec=httpx.Response)
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
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        await subject.report_task_status(123, "failed", "Error")

        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_report_task_status_with_empty_message(self, subject, mock_client):
        mock_response = Mock(spec=httpx.Response)
        mock_client.post.return_value = mock_response

        await subject.report_task_status(task_id=456, status="extracted")

        mock_client.post.assert_called_once_with(
            "/api/tasks/456/status",
            json={"status": "extracted", "message": ""}
        )
