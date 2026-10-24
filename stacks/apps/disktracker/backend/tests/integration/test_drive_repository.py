"""What drive persistence guarantees whatever its callers judged first: a drive collecting needs
is never registered under a capacity that is not its own, nor made without one."""

from collections.abc import Iterator
from uuid import UUID

import pytest

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.database import Database, Transactions
from disktracker.errors import CapacityConflict, CapacityRequired


@pytest.fixture
def transaction(database_url: str) -> Iterator[None]:
    database = Database(database_url)
    with Transactions(database).begin():
        yield
    database.dispose()


@pytest.fixture
def drives() -> DriveRepository:
    return DriveRepository()


def test_a_drive_is_registered_once_under_its_own_capacity(
    transaction: None, drives: DriveRepository
) -> None:
    made = drives.register("ST18000NM000J", 18000)

    assert isinstance(made, UUID)
    assert drives.register("ST18000NM000J", None) == made
    assert drives.register("ST18000NM000J", 18000) == made
    with pytest.raises(CapacityConflict, match="recorded as 18 TB"):
        drives.register("ST18000NM000J", 20000)


def test_a_drive_not_yet_known_is_not_registered_without_a_capacity(
    transaction: None, drives: DriveRepository
) -> None:
    with pytest.raises(CapacityRequired):
        drives.register("ST20000NM007D", None)
