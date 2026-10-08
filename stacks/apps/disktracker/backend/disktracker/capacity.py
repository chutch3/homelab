"""Capacities are whole decimal gigabytes (1 TB = 1000 GB), as drives and cards are sold."""

from decimal import Decimal


def capacity_label(gigabytes: int) -> str:
    if gigabytes < 1000:
        return f"{gigabytes} GB"
    return f"{format((Decimal(gigabytes) / 1000).normalize(), 'f')} TB"
