"""Unit tests for DownloadProgressTracker.

This is the owned abstraction over the filesystem-polling concern (a different
system dependency than the curl/tar subprocesses), so os.path.getsize/exists are
patched here directly — the one place that's appropriate. The clock is injected
(not patched globally) since asyncio's own wait_for uses the monotonic clock
internally; patching time.monotonic globally would starve it too.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from worker.progress import DownloadProgressTracker


class TestDownloadProgressTracker:
    def make_subject(self, clock_values):
        clock = iter(clock_values)
        return DownloadProgressTracker(interval=0, clock=lambda: next(clock))

    @pytest.mark.asyncio
    async def test_track_reports_downloaded_bytes_and_total(self):
        subject = self.make_subject([0.0, 1.0])
        calls = []
        stop_event = asyncio.Event()

        async def on_progress(downloaded, total, speed):
            calls.append((downloaded, total, speed))
            stop_event.set()

        with patch("os.path.exists", return_value=True), \
                patch("os.path.getsize", return_value=1000):
            await subject.track("/tmp/out.tgz", 5000, on_progress, stop_event)

        assert calls == [(1000, 5000, 1000.0)]

    @pytest.mark.asyncio
    async def test_track_computes_speed_from_byte_delta_over_time(self):
        subject = self.make_subject([0.0, 1.0, 3.0])
        calls = []
        sizes = iter([1000, 3000])
        stop_event = asyncio.Event()

        async def on_progress(downloaded, total, speed):
            calls.append((downloaded, total, speed))
            if len(calls) >= 2:
                stop_event.set()

        with patch("os.path.exists", return_value=True), \
                patch("os.path.getsize", side_effect=lambda _: next(sizes)):
            await subject.track("/tmp/out.tgz", 5000, on_progress, stop_event)

        assert calls[0] == (1000, 5000, 1000.0)
        assert calls[1] == (3000, 5000, 1000.0)  # (3000-1000) bytes / (3.0-1.0) sec

    @pytest.mark.asyncio
    async def test_track_reports_zero_bytes_when_file_does_not_exist_yet(self):
        subject = self.make_subject([0.0, 1.0])
        calls = []
        stop_event = asyncio.Event()

        async def on_progress(downloaded, total, speed):
            calls.append((downloaded, total, speed))
            stop_event.set()

        with patch("os.path.exists", return_value=False):
            await subject.track("/tmp/out.tgz", None, on_progress, stop_event)

        assert calls == [(0, None, 0.0)]

    @pytest.mark.asyncio
    async def test_track_exits_immediately_when_stop_event_already_set(self):
        subject = self.make_subject([0.0])
        on_progress = AsyncMock()
        stop_event = asyncio.Event()
        stop_event.set()

        await subject.track("/tmp/out.tgz", 5000, on_progress, stop_event)

        on_progress.assert_not_called()
