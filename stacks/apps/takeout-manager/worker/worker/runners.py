import asyncio
import logging
import os
import re
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

    async def probe_total_size(self, url: str, headers: dict[str, str]) -> int | None:
        """Reads the full chunk size off Content-Range via a cheap 1-byte range request,
        without downloading the body."""
        header_args: list[str] = []
        for key, value in headers.items():
            header_args.extend(["-H", f"{key}: {value}"])

        command = [
            "curl",
            url,
            "-r", "0-0",
            "-D", "-",
            "-o", "/dev/null",
            "--silent",
            "--show-error",
            *header_args,
        ]

        try:
            result = await asyncio.to_thread(
                subprocess.run, command, check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to probe total size for %s: %s", url, e.stderr)
            return None

        match = re.search(r"content-range:\s*bytes\s+\d+-\d+/(\d+)", result.stdout, re.IGNORECASE)
        return int(match.group(1)) if match else None


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

    async def verify(self, tgz_path: str) -> bool:
        command = ["tar", "-tzf", tgz_path]

        try:
            await asyncio.to_thread(
                subprocess.run, command, check=True, capture_output=True, text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error("Archive failed integrity check %s: %s", tgz_path, e.stderr)
            return False


class GpthRunner:
    """Wraps Google Photos Takeout Helper (Neo) — pairs each photo/video with its
    JSON sidecar and embeds the real capture date/GPS/etc as EXIF/XMP, organizing
    output into <output_dir>/<year>/<month>/...

    Flags verified against `gpth --help` output from the pinned binary (see
    Dockerfile GPTH_VERSION): --no-interactive is real (--[no-]interactive) and
    passed explicitly rather than relying on --input/--output implying it, since
    without it a bare `gpth --help` was observed to hang forever reading stdin —
    stdin is also pinned to DEVNULL below for the same reason. --albums nothing
    is used because MetadataService walks the whole output tree by extension
    without album awareness, so the default "shortcut" mode's symlinks would be
    double-counted and "ignore" mode silently deletes album-only files.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    async def process(self, input_dir: str, output_dir: str) -> bool:
        command = [
            "gpth",
            "--input", input_dir,
            "--output", output_dir,
            "--albums", "nothing",
            "--write-exif",
            "--divide-to-dates", "2",
            "--all-photos-dir", "",
            "--no-interactive",
        ]

        try:
            await asyncio.to_thread(
                subprocess.run,
                command,
                check=True,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
            )
            self.logger.info("Successfully processed metadata: %s -> %s", input_dir, output_dir)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error("GPTH processing failed: %s", e.stderr)
            return False
