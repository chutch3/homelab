import pytest

from disktracker.capacity import capacity_label


@pytest.mark.parametrize(
    ("gigabytes", "label"),
    [(18000, "18 TB"), (1920, "1.92 TB"), (1000, "1 TB"), (960, "960 GB"), (32, "32 GB")],
)
def test_capacity_label_uses_terabytes_from_one_terabyte_up(gigabytes: int, label: str) -> None:
    assert capacity_label(gigabytes) == label
