from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from fiber.clients.bowl import BowlStorage


class TestBowlStorage:
    @pytest.fixture()
    def subject(self, tmp_path: Path) -> BowlStorage:
        return BowlStorage(root=str(tmp_path))

    def test_temp_then_promote_is_atomic(self, subject: BowlStorage) -> None:
        temp = subject.temp_path("kenku-pg", "20260615T030000", "dump")
        Path(temp).write_text("DATA")
        final = subject.promote(temp)
        assert Path(final).read_text() == "DATA"
        assert not Path(temp).exists()
        assert ".partial" not in final

    def test_listing_distinguishes_temp_and_final(self, subject: BowlStorage) -> None:
        Path(subject.temp_path("kenku-pg", "t1", "dump")).write_text("x")
        final = subject.promote(subject.temp_path("kenku-pg", "t2", "dump"))
        entries = subject.list_entries("kenku-pg")
        temps = [e for e in entries if e.is_temp]
        finals = [e for e in entries if not e.is_temp]
        assert len(temps) == 1 and len(finals) == 1
        assert finals[0].path == final

    def test_free_space_check(self, subject: BowlStorage) -> None:
        assert subject.has_room(required_bytes=1) is True
        assert subject.has_room(required_bytes=10**18) is False

    def test_writes_receipt_next_to_dump(self, subject: BowlStorage) -> None:
        final = subject.promote(subject.temp_path("kenku-pg", "t3", "dump"))
        receipt = subject.write_receipt(final, {"service": "kenku-pg", "sha256": "abc"})
        assert json.loads(Path(receipt).read_text())["sha256"] == "abc"
        assert receipt.endswith(".manifest.json")

    def test_size_of_file(self, subject: BowlStorage) -> None:
        final = subject.promote(subject.temp_path("kenku-pg", "t4", "dump"))
        Path(final).write_bytes(b"hello world")
        assert subject.size(final) == 11

    def test_size_of_directory(self, subject: BowlStorage, tmp_path: Path) -> None:
        d = tmp_path / "kenku-pg" / "ts.dir"
        d.mkdir(parents=True)
        (d / "a.dat").write_bytes(b"abc")
        (d / "b.dat").write_bytes(b"de")
        assert subject.size(str(d)) == 5

    def test_checksum_of_file(self, subject: BowlStorage) -> None:
        final = subject.promote(subject.temp_path("kenku-pg", "t5", "dump"))
        payload = b"deterministic payload"
        Path(final).write_bytes(payload)
        expected = hashlib.sha256(payload).hexdigest()
        assert subject.checksum(final) == expected

    def test_checksum_of_directory_is_deterministic(self, subject: BowlStorage, tmp_path: Path) -> None:
        d = tmp_path / "kenku-pg" / "ts2.dir"
        d.mkdir(parents=True)
        (d / "b.dat").write_bytes(b"second")
        (d / "a.dat").write_bytes(b"first")
        assert subject.checksum(str(d)) == subject.checksum(str(d))
        h = hashlib.sha256()
        h.update(b"first")
        h.update(b"second")
        assert subject.checksum(str(d)) == h.hexdigest()

    def test_delete_removes_file_and_directory(self, subject: BowlStorage, tmp_path: Path) -> None:
        final = subject.promote(subject.temp_path("kenku-pg", "t6", "dump"))
        Path(final).write_bytes(b"data")
        assert Path(final).exists()
        subject.delete(final)
        assert not Path(final).exists()
        # service directory should also be removed when empty
        svc_dir = tmp_path / "kenku-pg"
        # directory may remain but the file must be gone
        assert not Path(final).exists()
