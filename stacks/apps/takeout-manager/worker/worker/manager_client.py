import logging
from typing import Any, AsyncGenerator, Optional

import httpx


async def init_async_client(manager_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=manager_url) as client:
        yield client


class ManagerClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    async def get_next_task(self) -> Optional[dict[str, Any]]:
        try:
            response = await self._client.get("/api/tasks/next")
            response.raise_for_status()
            task = response.json()
            return task if task and task.get("id") is not None else None
        except httpx.RequestError as e:
            self.logger.error("Could not connect to manager: %s", e)
            return None

    async def report_task_status(self, task_id: int, status: str, message: str = "") -> None:
        try:
            await self._client.post(
                f"/api/tasks/{task_id}/status",
                json={"status": status, "message": message},
            )
        except httpx.RequestError as e:
            self.logger.error("Could not report status for task %s: %s", task_id, e)
