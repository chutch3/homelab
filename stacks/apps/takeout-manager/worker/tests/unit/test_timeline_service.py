import pytest
from unittest.mock import AsyncMock

from worker.services import TimelineService
from worker.runners import TarRunner


class TestTimelineService:
    @pytest.fixture
    def mock_tar_runner(self):
        return AsyncMock(spec=TarRunner)

    @pytest.fixture
    def subject(self, mock_tar_runner, tmp_path):
        return TimelineService(
            tar_runner=mock_tar_runner, download_path=str(tmp_path / "downloads")
        )

    @pytest.fixture
    def downloads_dir(self, tmp_path):
        d = tmp_path / "downloads"
        d.mkdir()
        return d

    @pytest.mark.asyncio
    async def test_counts_media_per_month_from_filenames(
        self, subject, mock_tar_runner, downloads_dir
    ):
        (downloads_dir / "takeout-Z-001.tgz").write_bytes(b"a")
        mock_tar_runner.list_contents.return_value = [
            "Takeout/Google Photos/Album/PXL_20190705_120000.jpg",
            "Takeout/Google Photos/Album/PXL_20190712_120000.mp4",
            "Takeout/Google Photos/Album/PXL_20190802_120000.jpg",
            "Takeout/Google Photos/Album/IMG_20201225_000000.jpg",
            "Takeout/Google Photos/Album/metadata.json",  # not media -> skipped
            "Takeout/Google Photos/Album/undated.png",     # media, no date -> skipped
        ]

        success, months, _ = await subject.build_timeline(
            {"id": 4, "type": "timeline", "params": {"filename": "takeout-Z-001.tgz"}}
        )

        assert success is True
        assert months == {"2019-07": 2, "2019-08": 1, "2020-12": 1}
        called = mock_tar_runner.list_contents.await_args.args[0]
        assert called.endswith("takeout-Z-001.tgz")

    @pytest.mark.asyncio
    async def test_missing_filename(self, subject):
        success, months, _ = await subject.build_timeline({"id": 4, "params": {}})
        assert success is False
        assert months == {}

    @pytest.mark.asyncio
    async def test_archive_not_found(self, subject):
        success, months, _ = await subject.build_timeline(
            {"id": 4, "params": {"filename": "ghost.tgz"}}
        )
        assert success is False
