"""Integration tests for TarRunner against the real `tar` binary.

TarRunner is our owned abstraction over `tar`; it's exercised here with real
archives rather than by patching subprocess, so the actual tar behaviour (exit
codes, where the verbose member list is printed) is what's verified.
"""
import tarfile

import pytest

from worker.runners import TarRunner

pytestmark = pytest.mark.integration


def _make_tgz(path, names):
    with tarfile.open(path, "w:gz") as tar:
        for name in names:
            data = b"x"
            info = tarfile.TarInfo(name)
            info.size = len(data)
            import io

            tar.addfile(info, io.BytesIO(data))


class TestTarRunner:
    @pytest.fixture
    def subject(self):
        return TarRunner()

    @pytest.mark.asyncio
    async def test_extract_unpacks_files_and_returns_member_names(self, subject, tmp_path):
        archive = tmp_path / "a.tgz"
        _make_tgz(archive, ["PXL_20190705_1.jpg", "sub/PXL_20200101_2.mp4"])
        dest = tmp_path / "dest"

        names = await subject.extract(str(archive), str(dest))

        assert names is not None
        assert (dest / "PXL_20190705_1.jpg").exists()
        assert (dest / "sub" / "PXL_20200101_2.mp4").exists()
        # The returned member list is what a timeline is built from.
        joined = "\n".join(names)
        assert "PXL_20190705_1.jpg" in joined
        assert "PXL_20200101_2.mp4" in joined

    @pytest.mark.asyncio
    async def test_extract_returns_none_for_a_missing_archive(self, subject, tmp_path):
        result = await subject.extract(str(tmp_path / "nope.tgz"), str(tmp_path / "dest"))
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_returns_none_for_a_corrupt_archive(self, subject, tmp_path):
        bad = tmp_path / "bad.tgz"
        bad.write_bytes(b"not a real gzip archive")

        result = await subject.extract(str(bad), str(tmp_path / "dest"))
        assert result is None

    @pytest.mark.asyncio
    async def test_list_contents_returns_member_names_without_extracting(self, subject, tmp_path):
        archive = tmp_path / "a.tgz"
        _make_tgz(archive, ["PXL_20190705_1.jpg", "meta.json"])

        names = await subject.list_contents(str(archive))

        joined = "\n".join(names)
        assert "PXL_20190705_1.jpg" in joined
        assert "meta.json" in joined

    @pytest.mark.asyncio
    async def test_list_contents_returns_empty_for_a_corrupt_archive(self, subject, tmp_path):
        bad = tmp_path / "bad.tgz"
        bad.write_bytes(b"garbage")

        assert await subject.list_contents(str(bad)) == []

    @pytest.mark.asyncio
    async def test_verify_true_for_intact_and_false_for_corrupt(self, subject, tmp_path):
        good = tmp_path / "good.tgz"
        _make_tgz(good, ["a.jpg"])
        bad = tmp_path / "bad.tgz"
        bad.write_bytes(b"garbage")

        assert await subject.verify(str(good)) is True
        assert await subject.verify(str(bad)) is False
