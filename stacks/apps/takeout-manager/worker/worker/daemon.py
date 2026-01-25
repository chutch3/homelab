import asyncio
import logging

from dependency_injector.wiring import Provide, inject

from worker.containers import WorkerContainer
from worker.manager_client import ManagerClient
from worker.services import DownloadService


@inject
async def run_daemon(
    download_service: DownloadService = Provide[WorkerContainer.download_service],
    manager_client: ManagerClient = Provide[WorkerContainer.manager_client],
):
    logger = logging.getLogger(__name__)
    logger.info("Starting takeout worker...")
    while True:
        task = await manager_client.get_next_task()
        if task:
            task_id = task["id"]
            task_type = task["type"]

            logger.info(
                f"Processing task",
                extra={"task_id": task_id, "task_type": task_type},
            )

            if task_type == "download":
                success, message = await download_service.download_chunk(task)
                status = "downloaded" if success else "failed"
                logger.info(
                    f"Download {'succeeded' if success else 'failed'}: {message}",
                    extra={
                        "task_id": task_id,
                        "status": status,
                        "chunk_index": task.get("params", {}).get("chunk_index"),
                    },
                )
            elif task_type == "extract":
                success, message = await download_service.extract_chunk(task)
                status = "extracted" if success else "failed"
                logger.info(
                    f"Extraction {'succeeded' if success else 'failed'}: {message}",
                    extra={
                        "task_id": task_id,
                        "status": status,
                        "chunk_index": task.get("params", {}).get("chunk_index"),
                    },
                )
            else:
                success = False
                message = f"Unknown task type: {task_type}"
                logger.warning(
                    f"Unknown task type received",
                    extra={"task_id": task_id, "task_type": task_type},
                )
                status = "failed"

            await manager_client.report_task_status(task_id, status, message)

        else:
            logger.debug("No tasks available, sleeping...")
            await asyncio.sleep(30)
