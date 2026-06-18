from fiber.bristol import classify


def test_no_baseline_is_normal() -> None:
    assert classify(size_bytes=1234, baseline_median=None) == 4
    assert classify(size_bytes=1234, baseline_median=0) == 4


def test_ratio_thresholds() -> None:
    base = 1000
    assert classify(size_bytes=100, baseline_median=base) == 1    # <=0.2x suspiciously tiny
    assert classify(size_bytes=300, baseline_median=base) == 2    # <=0.5x
    assert classify(size_bytes=800, baseline_median=base) == 3    # <=0.9x
    assert classify(size_bytes=1000, baseline_median=base) == 4   # ~1x healthy
    assert classify(size_bytes=1300, baseline_median=base) == 5   # <=1.5x
    assert classify(size_bytes=1800, baseline_median=base) == 6   # <=2x
    assert classify(size_bytes=5000, baseline_median=base) == 7   # >2x bloated
