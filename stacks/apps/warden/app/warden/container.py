from __future__ import annotations

from datetime import timedelta

import httpx
from dependency_injector import containers, providers
from prometheus_client import CollectorRegistry

from warden.clients.arr import RadarrClient, SonarrClient
from warden.clients.prowlarr import ProwlarrClient
from warden.clock import SystemClock
from warden.config import Config
from warden.database import make_engine
from warden.metrics import Metrics
from warden.models import ArrClientProtocol, ArrType, QuotaSource
from warden.repositories.backoff import SearchBackoffRepository
from warden.repositories.efficacy import SearchAttemptRepository
from warden.repositories.ledger import SearchLedgerRepository
from warden.repositories.progress import QueueProgressRepository
from warden.schedule import ResetSchedule
from warden.services.backoff import BackoffTracker
from warden.services.efficacy import EfficacyTracker
from warden.services.orchestrator import TickOrchestrator
from warden.services.pacer import Pacer
from warden.services.planner import HuntPlanner
from warden.services.quota import QuotaLedger
from warden.services.quota_source import FallbackQuotaSource, ProwlarrQuotaSource
from warden.services.progress import ProgressTracker
from warden.services.stale import StaleDetector
from warden.services.sweeper import QueueSweeper


def _build_clients(config: Config, http: httpx.AsyncClient) -> list[ArrClientProtocol]:
    clients: list[ArrClientProtocol] = []
    for inst in config.instances:
        cls = RadarrClient if inst.type == ArrType.RADARR else SonarrClient
        clients.append(cls(name=inst.name, base_url=inst.url, http=http, api_key=inst.api_key))
    return clients


def _build_tracker(config: Config) -> ProgressTracker:
    return ProgressTracker(
        window_hours=config.stale_no_progress_hours,
        jitter_tolerance_bytes=config.stale_jitter_tolerance_mb * 1_000_000,
        enabled=config.stale_no_progress_enabled,
    )


def _build_efficacy(config: Config) -> EfficacyTracker:
    return EfficacyTracker(
        enabled=config.efficacy_enabled,
        resolve_window=timedelta(minutes=config.efficacy_resolve_minutes),
    )


def _build_backoff(config: Config) -> BackoffTracker:
    return BackoffTracker(
        enabled=config.backoff_enabled,
        threshold=config.backoff_miss_threshold,
        cooldown=timedelta(days=config.backoff_cooldown_days),
    )


def _build_quota_source(config: Config, http: httpx.AsyncClient) -> QuotaSource:
    if config.prowlarr_url and config.prowlarr_api_key:
        client = ProwlarrClient(base_url=config.prowlarr_url, http=http,
                                api_key=config.prowlarr_api_key)
        return ProwlarrQuotaSource(client, default_query_limit=config.default_query_limit)
    return FallbackQuotaSource()


class Container(containers.DeclarativeContainer):
    config = providers.Singleton(Config.from_env)
    registry = providers.Singleton(CollectorRegistry)
    metrics = providers.Singleton(Metrics, registry=registry)
    clock = providers.Singleton(SystemClock)
    engine = providers.Singleton(make_engine, url=config.provided.db_url)
    ledger = providers.Singleton(SearchLedgerRepository, engine=engine)
    http = providers.Singleton(httpx.AsyncClient, timeout=30.0)
    clients = providers.Singleton(_build_clients, config=config, http=http)
    quota_source = providers.Singleton(_build_quota_source, config=config, http=http)
    schedule = providers.Singleton(ResetSchedule, reset_at_local=config.provided.reset_at_local, tz=config.provided.tz)
    quota = providers.Singleton(
        QuotaLedger,
        reserve_pct=config.provided.reserve_pct,
        fallback_budget=config.provided.fallback_searches_per_day,
        schedule=schedule,
    )
    pacer = providers.Singleton(Pacer, poll_interval_sec=config.provided.poll_interval_sec)
    planner = providers.Singleton(HuntPlanner)
    detector = providers.Singleton(StaleDetector, grace_hours=config.provided.stale_grace_hours)
    sweeper = providers.Singleton(
        QueueSweeper,
        detector=detector,
        enabled=config.provided.stale_sweep_enabled,
        max_removals_per_tick=config.provided.stale_max_removals_per_tick,
        mass_fraction=config.provided.stale_mass_fraction,
        min_queue_for_guard=config.provided.stale_min_queue_for_guard,
    )
    tracker = providers.Singleton(_build_tracker, config=config)
    progress_repo = providers.Singleton(QueueProgressRepository, engine=engine)
    efficacy = providers.Singleton(_build_efficacy, config=config)
    efficacy_repo = providers.Singleton(SearchAttemptRepository, engine=engine)
    backoff = providers.Singleton(_build_backoff, config=config)
    backoff_repo = providers.Singleton(SearchBackoffRepository, engine=engine)
    orchestrator = providers.Singleton(
        TickOrchestrator,
        clients=clients,
        quota=quota,
        pacer=pacer,
        planner=planner,
        sweeper=sweeper,
        tracker=tracker,
        progress_repo=progress_repo,
        efficacy=efficacy,
        efficacy_repo=efficacy_repo,
        backoff=backoff,
        backoff_repo=backoff_repo,
        ledger=ledger,
        clock=clock,
        metrics=metrics,
        schedule=schedule,
        quota_source=quota_source,
        include_cutoff_unmet=config.provided.include_cutoff_unmet,
        fallback_per_day=config.provided.fallback_searches_per_day,
        prowlarr_fallback_on_error=config.provided.prowlarr_fallback_on_error,
        poll_interval_sec=config.provided.poll_interval_sec,
    )
