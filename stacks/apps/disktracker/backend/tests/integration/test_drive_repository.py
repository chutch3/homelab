"""What drive persistence guarantees whatever its callers judged first: a drive collecting needs
is never registered under a capacity that is not its own, nor made without one."""

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.errors import CapacityConflict, CapacityRequired


@pytest.fixture
def session(database_url: str) -> Iterator[Session]:
    engine = create_engine(database_url)
    with Session(engine) as opened:
        yield opened
    engine.dispose()


@pytest.fixture
def drives() -> DriveRepository:
    return DriveRepository(next_id=uuid4)


def test_a_drive_is_registered_once_under_its_own_capacity(
    session: Session, drives: DriveRepository
) -> None:
    made = drives.register(session, "ST18000NM000J", 18000)

    assert isinstance(made, UUID)
    assert drives.register(session, "ST18000NM000J", None) == made
    assert drives.register(session, "ST18000NM000J", 18000) == made
    with pytest.raises(CapacityConflict, match="recorded as 18 TB"):
        drives.register(session, "ST18000NM000J", 20000)


def test_a_drive_not_yet_known_is_not_registered_without_a_capacity(
    session: Session, drives: DriveRepository
) -> None:
    with pytest.raises(CapacityRequired):
        drives.register(session, "ST20000NM007D", None)
