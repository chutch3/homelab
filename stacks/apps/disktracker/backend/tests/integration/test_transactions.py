"""What a transactional method guarantees: what it does is kept when it returns and none of it when
it raises, a method it calls is part of it, and nothing works on the database outside one."""

from collections.abc import Iterator

import pytest
from sqlalchemy import text

from disktracker.database import (
    Database,
    NotInTransaction,
    Transactions,
    current_session,
    transactional,
)


class Rules:
    """Writes and reads condition rules as a repository would: on the transaction it is in."""

    def add(self, position: int) -> None:
        current_session().execute(
            text("INSERT INTO condition_rules VALUES (:position, 'x', 'new')"),
            {"position": position},
        )

    def positions(self) -> list[int]:
        return list(
            current_session().scalars(
                text("SELECT position FROM condition_rules WHERE position >= 900")
            )
        )


class Service:
    def __init__(self, transactions: Transactions) -> None:
        self.transactions, self.rules = transactions, Rules()

    @transactional
    def add(self, *positions: int, then_fail: bool = False) -> None:
        for position in positions:
            self.rules.add(position)
        if then_fail:
            raise RuntimeError("refused")

    @transactional
    def add_through(self, position: int, then_fail: bool) -> None:
        self.add(position)
        if then_fail:
            raise RuntimeError("refused")

    @transactional(read_only=True)
    def positions(self) -> list[int]:
        return self.rules.positions()

    @transactional(read_only=True)
    def add_while_reading(self, position: int) -> None:
        self.add(position)

    @transactional
    def positions_while_writing(self, position: int) -> list[int]:
        self.rules.add(position)
        return self.positions()


@pytest.fixture
def database(database_url: str) -> Iterator[Database]:
    opened = Database(database_url)
    yield opened
    opened.dispose()


@pytest.fixture
def subject(database: Database) -> Service:
    return Service(Transactions(database))


def test_what_a_method_does_is_kept_when_it_returns_and_none_of_it_when_it_raises(
    subject: Service,
) -> None:
    subject.add(900, 901)
    with pytest.raises(RuntimeError):
        subject.add(902, 903, then_fail=True)

    assert subject.positions() == [900, 901]


def test_a_method_another_calls_is_part_of_its_transaction(subject: Service) -> None:
    with pytest.raises(RuntimeError):
        subject.add_through(900, then_fail=True)
    subject.add_through(901, then_fail=False)

    assert subject.positions() == [901]


def test_a_read_sees_what_the_writing_it_is_part_of_has_done(subject: Service) -> None:
    assert subject.positions_while_writing(900) == [900]


def test_nothing_is_written_from_within_a_read(subject: Service) -> None:
    with pytest.raises(NotInTransaction, match="read"):
        subject.add_while_reading(900)

    assert subject.positions() == []


def test_nothing_works_on_the_database_outside_a_transaction() -> None:
    with pytest.raises(NotInTransaction):
        Rules().positions()
