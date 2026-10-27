from __future__ import annotations

import pytest

from warden.profiles.storage import filesystem_at, require_local_filesystem


@pytest.mark.parametrize("filesystem", ["ocfs2", "nfs4", "cifs", "overlay", "unknown"])
def test_rejects_shared_or_unverified_output_filesystems(filesystem: str) -> None:
    mounts = f"1 0 0:1 / / rw - {filesystem} storage rw\n"
    with pytest.raises(ValueError, match="verified local filesystem"):
        require_local_filesystem("/output/catalog", mounts)


def test_accepts_local_mount_nested_under_shared_mount() -> None:
    mounts = "1 0 0:1 / / rw - ocfs2 storage rw\n2 1 0:2 / /local rw - tmpfs tmpfs rw\n"
    assert require_local_filesystem("/local/catalog", mounts) is None


def test_mount_prefix_must_end_at_path_boundary() -> None:
    mounts = "1 0 0:1 / / rw - ocfs2 storage rw\n2 1 0:2 / /local rw - tmpfs tmpfs rw\n"
    with pytest.raises(ValueError, match="verified local filesystem"):
        require_local_filesystem("/local-other/catalog", mounts)


def test_rejects_unknown_mounts() -> None:
    with pytest.raises(ValueError, match="verified local filesystem"):
        require_local_filesystem("/output/catalog", "")


def test_conflicting_mounts_at_same_path_fail_closed() -> None:
    mounts = "1 0 0:1 / / rw - tmpfs tmpfs rw\n2 1 0:2 / / rw - ocfs2 storage rw\n"
    with pytest.raises(ValueError, match="verified local filesystem"):
        require_local_filesystem("/output/catalog", mounts)


@pytest.mark.parametrize(("path", "mountinfo", "expected"), [
    ("/local data/profiles", "1 0 0:1 / / rw - ocfs2 disk rw\n2 1 0:2 / /local\\040data rw - tmpfs tmpfs rw", "tmpfs"),
    ("/local-other/profiles", "1 0 0:1 / / rw - ocfs2 disk rw\n2 1 0:2 / /local rw - ext4 disk rw", "ocfs2"),
    ("/profiles", "malformed\n1 0 0:1 / / rw -", "unknown or ambiguous"),
    ("/profiles", "1 0 0:1 / / rw - ext4 disk rw\n2 0 0:2 / / rw - ocfs2 disk rw", "unknown or ambiguous"),
])
def test_filesystem_at_resolves_mounts(path: str, mountinfo: str, expected: str) -> None:
    assert filesystem_at(path, mountinfo) == expected
