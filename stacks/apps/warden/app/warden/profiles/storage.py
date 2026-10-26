from __future__ import annotations

import posixpath


def require_local_filesystem(path: str, mountinfo: str) -> None:
    """Fail closed on shared/unknown filesystem types, using caller-supplied mount data."""
    candidates: list[tuple[int, str]] = []
    for line in mountinfo.splitlines():
        before, separator, after = line.partition(" - ")
        fields = before.split()
        if not separator or len(fields) < 5 or not after.split():
            continue
        mount = fields[4]
        for escaped, decoded in (("\\040", " "), ("\\011", "\t"), ("\\012", "\n"), ("\\134", "\\")):
            mount = mount.replace(escaped, decoded)
        if posixpath.commonpath([path, mount]) == mount:
            candidates.append((len(mount), after.split()[0]))
    longest = max((length for length, _ in candidates), default=0)
    filesystems = {kind for length, kind in candidates if length == longest}
    filesystem = next(iter(filesystems)) if len(filesystems) == 1 else "unknown or ambiguous"
    if filesystem not in {"ext4", "xfs", "btrfs", "tmpfs"}:
        raise ValueError(f"{path}: output requires a verified local filesystem; found {filesystem}")
