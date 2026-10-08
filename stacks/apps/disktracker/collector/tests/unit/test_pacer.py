import pytest

from collector.pacer import Pacer
from tests.fakes import FakeClock


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def subject(clock: FakeClock) -> Pacer:
    return Pacer(clock)


def test_the_first_request_to_a_site_never_waits(subject: Pacer, clock: FakeClock) -> None:
    subject.wait_turn("https://a.test", 2)
    assert clock.sleeps == []


def test_a_request_within_the_delay_waits_only_the_rest_of_it(
    subject: Pacer, clock: FakeClock
) -> None:
    subject.wait_turn("https://a.test", 2)
    clock.advance(0.5)
    subject.wait_turn("https://a.test", 2)
    assert clock.sleeps == [1.5]


def test_a_request_after_the_delay_has_passed_does_not_wait(
    subject: Pacer, clock: FakeClock
) -> None:
    subject.wait_turn("https://a.test", 2)
    clock.advance(3)
    subject.wait_turn("https://a.test", 2)
    assert clock.sleeps == []


def test_each_site_keeps_its_own_turns(subject: Pacer, clock: FakeClock) -> None:
    subject.wait_turn("https://a.test", 2)
    subject.wait_turn("https://b.test", 2)
    assert clock.sleeps == []


def test_a_site_without_a_delay_never_waits(subject: Pacer, clock: FakeClock) -> None:
    subject.wait_turn("https://a.test", None)
    subject.wait_turn("https://a.test", None)
    assert clock.sleeps == []
