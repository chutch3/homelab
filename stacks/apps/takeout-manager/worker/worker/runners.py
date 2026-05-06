import asyncio
import logging
import os
import subprocess


class CurlRunner:
    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self.logger = logging.getLogger(self.__class__.__name__)

    async def download(self, url: str, output_path: str, headers: dict[str, str]) -> bool:
        header_args: list[str] = []
        for key, value in headers.items():
            header_args.extend(["-H", f"{key}: {value}"])

        command = [
            "curl",
            url,
            "--compressed",
            "-C", "-",
            "--fail",
            "--silent",
            "--show-error",
            "--output",
            output_path,
            *header_args,
        ]

        for attempt in range(1, self.max_retries + 1):
            try:
                await asyncio.to_thread(
                    subprocess.run, command, check=True, capture_output=True, text=True
                )
                self.logger.info("Successfully downloaded to %s", output_path)
                return True
            except subprocess.CalledProcessError as e:
                if e.returncode == 22:
                    stderr = e.stderr or ""
                    if "401" in stderr or "404" in stderr:
                        self.logger.error("Non-retryable error downloading: %s", stderr)
                        return False
                if attempt < self.max_retries:
                    self.logger.warning("Download attempt %d failed, retrying...", attempt)
                    await asyncio.sleep(1 * attempt)
                else:
                    self.logger.error("Download failed after %d attempts", self.max_retries)
                    return False

        return False


class TarRunner:
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    async def extract(self, tgz_path: str, dest_dir: str) -> bool:
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception as e:
            self.logger.error("Failed to create directory %s: %s", dest_dir, e)
            return False

        command = ["tar", "-xzf", tgz_path, "-C", dest_dir]

        try:
            await asyncio.to_thread(
                subprocess.run, command, check=True, capture_output=True, text=True
            )
            self.logger.info("Successfully extracted %s to %s", tgz_path, dest_dir)
            return True
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            if "Unexpected EOF" in stderr or "damaged" in stderr:
                self.logger.error("Corrupted archive: %s", tgz_path)
            elif "No such file or directory" in stderr:
                self.logger.error("Source file not found: %s", tgz_path)
            elif "No space left on device" in stderr:
                self.logger.error("Insufficient disk space for extraction")
            elif "Permission denied" in stderr:
                self.logger.error("Permission denied accessing %s", dest_dir)
            else:
                self.logger.error("Extraction failed: %s", stderr)
            return False
