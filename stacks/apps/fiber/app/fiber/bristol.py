from __future__ import annotations


def classify(size_bytes: int, baseline_median: int | None) -> int:
    if not baseline_median:
        return 4
    ratio = size_bytes / baseline_median
    if ratio <= 0.2:
        return 1
    if ratio <= 0.5:
        return 2
    if ratio <= 0.9:
        return 3
    if ratio <= 1.1:
        return 4
    if ratio <= 1.5:
        return 5
    if ratio <= 2.0:
        return 6
    return 7
