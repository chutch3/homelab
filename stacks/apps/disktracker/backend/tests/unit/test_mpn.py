import pytest

from disktracker.mpn import normalize_mpn


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ST18000NM000J", "ST18000NM000J"),
        (" st18000nm000j ", "ST18000NM000J"),
        ("ST18000 NM000J", "ST18000NM000J"),
        ("wuh721818ale6l4\t", "WUH721818ALE6L4"),
        ("ST18000NM000J-2E3101", "ST18000NM000J-2E3101"),
    ],
)
def test_normalize_mpn(raw: str, expected: str) -> None:
    assert normalize_mpn(raw) == expected
