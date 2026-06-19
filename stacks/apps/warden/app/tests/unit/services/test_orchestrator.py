import logging

from prometheus_client import CollectorRegistry

from warden.clock import SystemClock
from warden.metrics import Metrics
from warden.models import ArrType, WantedItem, WantKind
from warden.repositories.ledger import SearchLedgerRepository
from warden.schedule import ResetSchedule
from warden.services.orchestrator import TickOrchestrator
from warden.services.pacer import Pacer
from warden.services.planner import HuntPlanner
from warden.services.quota import QuotaLedger
from warden.services.quota_source import FallbackQuotaSource
from warden.services.stale import StaleDetector
from warden.services.sweeper import QueueSweeper


class StubClient:
    """Minimal ArrClientProtocol double for a unit test of the hunt logging."""

    def __init__(self, missing, cutoff=None, arr_type: ArrType = ArrType.SONARR) -> None:
        self.name = arr_type.value
        self.arr_type = arr_type
        self._missing = missing
        self._cutoff = cutoff or []
        self.searched: list[list[int]] = []

    async def list_missing(self) -> list[WantedItem]:
        return list(self._missing)

    async def list_cutoff_unmet(self) -> list[WantedItem]:
        return list(self._cutoff)

    async def trigger_search(self, ids: list[int]) -> None:
        self.searched.append(ids)

    async def list_queue(self):
        return []

    async def remove_queue_item(self, queue_id, *, remove_from_client=True, blocklist=True):
        return None


def _sweeper() -> QueueSweeper:
    return QueueSweeper(StaleDetector(grace_hours=48), enabled=True, max_removals_per_tick=5,
                        mass_fraction=0.5, min_queue_for_guard=3)


def _make_orch(clients, repo: SearchLedgerRepository) -> TickOrchestrator:
    schedule = ResetSchedule("00:00")
    return TickOrchestrator(
        clients=clients,
        quota=QuotaLedger(reserve_pct=20, fallback_budget=200, schedule=schedule),
        pacer=Pacer(poll_interval_sec=300),
        planner=HuntPlanner(),
        sweeper=_sweeper(),
        ledger=repo,
        clock=SystemClock(),
        metrics=Metrics(CollectorRegistry()),
        schedule=schedule,
        quota_source=FallbackQuotaSource(),
        include_cutoff_unmet=True,
        fallback_per_day=200,
        prowlarr_fallback_on_error=True,
        poll_interval_sec=300,
    )


def _events(caplog, event: str):
    return [r for r in caplog.records if getattr(r, "event", None) == event]


class TestHuntLogging:
    async def test_logs_search_triggered_per_item(self, repo, caplog):
        item = WantedItem(instance="sonarr", remote_id=123, title="The Bear S03E01", kind=WantKind.MISSING)
        client = StubClient([item], arr_type=ArrType.SONARR)
        orch = _make_orch([client], repo)
        with caplog.at_level(logging.INFO, logger="warden.orchestrator"):
            issued = await orch._hunt_one(client, 5, "sonarr:2026-06-18", [item], [], set())
        assert issued == 1
        assert client.searched == [[123]]
        recs = _events(caplog, "search_triggered")
        assert len(recs) == 1
        r = recs[0]
        assert r.source == "sonarr"
        assert r.arr_type == "sonarr"
        assert r.id == 123
        assert r.title == "The Bear S03E01"
        assert r.kind == "missing"

    async def test_logs_nothing_to_hunt_when_empty(self, repo, caplog):
        client = StubClient([], arr_type=ArrType.RADARR)
        orch = _make_orch([client], repo)
        with caplog.at_level(logging.INFO, logger="warden.orchestrator"):
            issued = await orch._hunt_one(client, 5, "radarr:2026-06-18", [], [], set())
        assert issued == 0
        assert client.searched == []
        recs = _events(caplog, "nothing_to_hunt")
        assert len(recs) == 1
        assert recs[0].source == "radarr"
        assert recs[0].missing == 0
        assert recs[0].cutoff == 0
