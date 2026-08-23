import asyncio
import logging

from dependency_injector.wiring import Provide, inject

from worker.containers import WorkerContainer
from worker.manager_client import ManagerClient
from worker.services import DownloadService, MetadataService, TimelineService


@inject
async def run_daemon(
    download_service: DownloadService = Provide[WorkerContainer.download_service],
    metadata_service: MetadataService = Provide[WorkerContainer.metadata_service],
    timeline_service: TimelineService = Provide[WorkerContainer.timeline_service],
    manager_client: ManagerClient = Provide[WorkerContainer.manager_client],
) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Starting takeout worker...")
    while True:
        task = await manager_client.get_next_task()
        if task:
            task_id = task["id"]
            task_type = task["type"]

            logger.info(
                "Processing task",
                extra={"task_id": task_id, "task_type": task_type},
            )

            if task_type == "download":
                async def report_progress(
                    downloaded_bytes: int, total_bytes, speed_bytes_per_sec: float
                ) -> None:
                    await manager_client.report_task_progress(
                        task_id, downloaded_bytes, total_bytes, speed_bytes_per_sec
                    )

                success, message = await download_service.download_chunk(
                    task, on_progress=report_progress
                )
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
                # The whole-export GPTH pass is the extraction.
                success, message, timelines = await metadata_service.process_job_metadata(task)
                status = "completed" if success else "failed"
                logger.info(
                    f"Extraction {'succeeded' if success else 'failed'}: {message}",
                    extra={"task_id": task_id, "status": status},
                )
                await manager_client.report_metadata_task_status(task_id, status, message)
                for archive_name, months in timelines.items():
                    await manager_client.report_timeline(archive_name, months)
                continue
            elif task_type == "extract_archive":
                success, message, timelines = await metadata_service.extract_single_archive(task)
                status = "extracted" if success else "failed"
                logger.info(
                    f"Archive extraction {'succeeded' if success else 'failed'}: {message}",
                    extra={"task_id": task_id, "status": status},
                )
                await manager_client.report_archive_extraction_status(task_id, status, message)
                for archive_name, months in timelines.items():
                    await manager_client.report_timeline(archive_name, months)
                continue
            elif task_type == "timeline":
                filename = task.get("params", {}).get("filename")
                success, months, message = await timeline_service.build_timeline(task)
                if success:
                    await manager_client.report_timeline(filename, months)
                    logger.info("Timeline built: %s", message, extra={"task_id": task_id})
                else:
                    logger.warning("Timeline failed: %s", message, extra={"task_id": task_id})
                continue
            else:
                success = False
                message = f"Unknown task type: {task_type}"
                logger.warning(
                    "Unknown task type received",
                    extra={"task_id": task_id, "task_type": task_type},
                )
                status = "failed"

            await manager_client.report_task_status(task_id, status, message)

        else:
            logger.debug("No tasks available, sleeping...")
            await asyncio.sleep(30)
