from fiber.status import DBStatus
from fiber.view import CardVM, Counts, DashboardVM


def _card(st: DBStatus) -> CardVM:
    return CardVM(
        service="x",
        engine="postgres",
        status=st,
        last_rel="4h ago",
        size="1 GB",
        next_run="03:00",
        bristol=4,
        writes_to="/backups/x",
        error=None,
    )


def test_counts_and_verdict() -> None:
    cards = [_card(DBStatus.CLEAN), _card(DBStatus.CLEAN), _card(DBStatus.CLOGGED)]
    vm = DashboardVM(
        cards=cards,
        counts=Counts.from_cards(cards),
        discovery=[],
        bowl_path="/backups",
        bowl_used="16 GB",
        bowl_free="104 GB",
    )
    assert vm.counts.by_status[DBStatus.CLEAN] == 2
    assert vm.needs_attention == 1  # clogged
    assert vm.verdict_ok is False


from fiber.view import DrawerVM


class TestDrawerVM:
    def test_is_frozen_dataclass(self) -> None:
        vm = DrawerVM(
            service="kenku-pg",
            engine="postgres",
            status=DBStatus.CLEAN,
            plain="Backed up on schedule",
            last_rel="4h ago",
            size="88 MB",
            next_run="tomorrow 03:00",
            writes_to="/backups",
            bristol=4,
            app_version="kenku:0.28.1",
            sha="abc123",
            fmt="custom",
            timeline=[("4h ago", "clean"), ("yest", "clean")],
            sample=None,
            labels='deploy:\n  labels:\n    - "fiber.enable=true"',
            error=None,
        )
        assert vm.service == "kenku-pg"
        assert vm.bristol == 4
        assert vm.timeline == [("4h ago", "clean"), ("yest", "clean")]

    def test_immutable(self) -> None:
        import pytest
        vm = DrawerVM(
            service="s", engine="postgres", status=DBStatus.CLEAN,
            plain="ok", last_rel="now", size="1 MB", next_run="—",
            writes_to="/backups", bristol=None, app_version=None,
            sha=None, fmt="custom", timeline=[], sample=None,
            labels="", error=None,
        )
        with pytest.raises((AttributeError, TypeError)):
            vm.service = "other"  # type: ignore[misc]
