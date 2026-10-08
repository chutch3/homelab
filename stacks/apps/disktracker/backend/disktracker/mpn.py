"""One canonical spelling per MPN, so case and stray spacing never split a drive."""

import re


def normalize_mpn(raw: str) -> str:
    return re.sub(r"\s+", "", raw).upper()
