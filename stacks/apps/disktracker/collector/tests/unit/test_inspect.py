import pytest

from collector.inspect import run_time


@pytest.mark.parametrize(
    ("requests", "seconds_apart", "said"),
    [
        (3, 2, "under a minute (3 requests, 2 seconds apart)"),
        (150, 20, "about 50 minutes (150 requests, 20 seconds apart)"),
        (10_607, 2, "about 6 hours (10,607 requests, 2 seconds apart)"),
        (40, 2, "about 1 minute (40 requests, 2 seconds apart)"),
        (1800, 2, "about 1 hour (1,800 requests, 2 seconds apart)"),
        (120_000, 2, "about 3 days (120,000 requests, 2 seconds apart)"),
        (30_000, 2.5, "about 21 hours (30,000 requests, 2.5 seconds apart)"),
        (3, 1, "under a minute (3 requests, 1 second apart)"),
        (1, 20, "under a minute (1 request, 20 seconds apart)"),
    ],
)
def test_how_long_a_run_would_take_is_said_roughly(
    requests: int, seconds_apart: float, said: str
) -> None:
    assert run_time(requests, seconds_apart) == said
