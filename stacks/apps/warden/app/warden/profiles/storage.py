from __future__ import annotations

import posixpath


def filesystem_at(path: str, mountinfo: str) -> str:
    """Find the most specific mount; conflicting entries cannot establish a type."""
    best_length = -1
    filesystems: set[str] = set()
    for line in mountinfo.splitlines():
        before, separator, after = line.partition(" - ")
        mount_fields = before.split()
        filesystem_fields = after.split()
        if not separator or len(mount_fields) < 5 or not filesystem_fields:
            continue
        mount = mount_fields[4]
        for escaped, decoded in (("\\040", " "), ("\\011", "\t"), ("\\012", "\n"), ("\\134", "\\")):
            mount = mount.replace(escaped, decoded)
        if posixpath.commonpath([path, mount]) != mount:
            continue
        if len(mount) > best_length:
            best_length = len(mount)
            filesystems.clear()
        if len(mount) == best_length:
            filesystems.add(filesystem_fields[0])
    return next(iter(filesystems)) if len(filesystems) == 1 else "unknown or ambiguous"


def require_local_filesystem(path: str, mountinfo: str) -> None:
    """Allow only approved filesystem types for profile export and disposable cache."""
    filesystem = filesystem_at(path, mountinfo)
    if filesystem not in {"ext4", "xfs", "btrfs", "tmpfs"}:
        raise ValueError(f"{path}: output requires a verified local filesystem; found {filesystem}")
