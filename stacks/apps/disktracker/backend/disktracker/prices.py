"""Pure cost calculations; all amounts arrive in integer USD cents, capacities in whole GB."""

from decimal import ROUND_HALF_UP, Decimal


def comparable_price(item: int, shipping: int | None, capacity_gb: int) -> tuple[int, str]:
    """Unknown shipping (None) counts as zero; callers flag it separately."""
    total = item + (shipping or 0)
    # cents / 100 = dollars; gigabytes / 1000 = terabytes.
    per_tb = (Decimal(total) * 10 / capacity_gb).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return total, str(per_tb)
