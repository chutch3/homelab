from __future__ import annotations

import asyncio
import os
from datetime import timedelta

import httpx
import uvicorn
from dependency_injector import containers, providers
from fastapi import FastAPI
from prometheus_client import CollectorRegistry

from warden.arr_service import ArrService
from warden.clients.arr import RadarrClient, SonarrClient
from warden.clients.git import GitClient
from warden.clients.prowlarr import ProwlarrClient
from warden.clock import SystemClock
from warden.config import Config
from warden.database import make_engine
from warden.logger import emit_profile_event
from warden.loop import _hunt_loop
from warden.metrics import Metrics
from warden.profiles.cache import SnapshotCache
from warden.profiles.codec import YamlJsonCodec, profile_schemas
from warden.profiles.files import LocalProfileFiles, ProfileStore
from warden.profiles.loop import run_profiles
from warden.profiles.observer import Observer
from warden.profiles.settings import ProfileSettings
from warden.profiles.sources import DirectoryProfileSource, GitProfileSource
from warden.repositories.backoff import SearchBackoffRepository
from warden.repositories.efficacy import SearchAttemptRepository
from warden.repositories.ledger import SearchLedgerRepository
from warden.repositories.progress import QueueProgressRepository
from warden.schedule import ResetSchedule
from warden.serve import create_app, serve
from warden.services.backoff import BackoffTracker
from warden.services.efficacy import EfficacyTracker
from warden.services.orchestrator import TickOrchestrator
from warden.services.pacer import Pacer
from warden.services.planner import HuntPlanner
from warden.services.quota import QuotaLedger
from warden.services.quota_source import FallbackQuotaSource, ProwlarrQuotaSource
from warden.services.progress import ProgressTracker
from warden.services.space import SpaceGuard
from warden.services.stale import StaleDetector
from warden.services.sweeper import QueueSweeper


class Container(containers.DeclarativeContainer):
    environment = providers.Singleton(dict, os.environ)
    config = providers.Singleton(Config.from_env, env=environment)
    registry = providers.Singleton(CollectorRegistry)
    metrics = providers.Singleton(Metrics, registry=registry)
    clock = providers.Singleton(SystemClock)
    engine = providers.Singleton(make_engine, url=config.provided.db_url)
    ledger = providers.Singleton(SearchLedgerRepository, engine=engine)

    # Resource owns AsyncClient's context and closes it when the command exits.
    http = providers.Resource(httpx.AsyncClient, timeout=30.0)
    radarr_client = providers.Singleton(
        RadarrClient, name="radarr", http=http,
        base_url=environment.provided.get.call("WARDEN_RADARR_URL", ""),
        api_key=environment.provided.get.call("WARDEN_RADARR_API_KEY", ""),
    )
    sonarr_client = providers.Singleton(
        SonarrClient, name="sonarr", http=http,
        base_url=environment.provided.get.call("WARDEN_SONARR_URL", ""),
        api_key=environment.provided.get.call("WARDEN_SONARR_API_KEY", ""),
    )
    radarr = providers.Selector(
        providers.Callable(lambda env: "enabled" if env.get("WARDEN_RADARR_URL") and env.get("WARDEN_RADARR_API_KEY") else "disabled", environment),
        enabled=radarr_client, disabled=providers.Object(None),
    )
    sonarr = providers.Selector(
        providers.Callable(lambda env: "enabled" if env.get("WARDEN_SONARR_URL") and env.get("WARDEN_SONARR_API_KEY") else "disabled", environment),
        enabled=sonarr_client, disabled=providers.Object(None),
    )
    arr_clients = providers.Callable(lambda **clients: {name: client for name, client in clients.items() if client is not None}, radarr=radarr, sonarr=sonarr)
    clients = providers.Callable(lambda clients: list(clients.values()), arr_clients)
    arr_service = providers.Singleton(ArrService, clients=arr_clients)

    prowlarr_client = providers.Singleton(
        ProwlarrClient, base_url=config.provided.prowlarr_url, http=http, api_key=config.provided.prowlarr_api_key,
    )
    prowlarr_quota = providers.Singleton(
        ProwlarrQuotaSource, client=prowlarr_client, default_query_limit=config.provided.default_query_limit,
    )
    fallback_quota = providers.Singleton(FallbackQuotaSource)
    quota_source = providers.Selector(
        providers.Callable(lambda cfg: "prowlarr" if cfg.prowlarr_url and cfg.prowlarr_api_key else "fallback", config),
        prowlarr=prowlarr_quota, fallback=fallback_quota,
    )
    schedule = providers.Singleton(ResetSchedule, reset_at_local=config.provided.reset_at_local, tz=config.provided.tz)
    quota = providers.Singleton(
        QuotaLedger, reserve_pct=config.provided.reserve_pct,
        fallback_budget=config.provided.fallback_searches_per_day, schedule=schedule,
    )
    pacer = providers.Singleton(Pacer, poll_interval_sec=config.provided.poll_interval_sec)
    planner = providers.Singleton(HuntPlanner)
    space_guard = providers.Singleton(SpaceGuard, min_free_bytes=config.provided.min_free_bytes)
    detector = providers.Singleton(StaleDetector, grace_hours=config.provided.stale_grace_hours)
    sweeper = providers.Singleton(
        QueueSweeper, detector=detector,
        enabled=config.provided.stale_sweep_enabled,
        max_removals_per_tick=config.provided.stale_max_removals_per_tick,
        mass_fraction=config.provided.stale_mass_fraction,
        min_queue_for_guard=config.provided.stale_min_queue_for_guard,
    )
    tracker = providers.Singleton(
        ProgressTracker, window_hours=config.provided.stale_no_progress_hours,
        jitter_tolerance_bytes=providers.Callable(lambda mb: mb * 1_000_000, config.provided.stale_jitter_tolerance_mb),
        enabled=config.provided.stale_no_progress_enabled,
    )
    progress_repo = providers.Singleton(QueueProgressRepository, engine=engine)
    efficacy = providers.Singleton(
        EfficacyTracker, enabled=config.provided.efficacy_enabled,
        resolve_window=providers.Callable(timedelta, minutes=config.provided.efficacy_resolve_minutes),
    )
    efficacy_repo = providers.Singleton(SearchAttemptRepository, engine=engine)
    backoff = providers.Singleton(
        BackoffTracker, enabled=config.provided.backoff_enabled, threshold=config.provided.backoff_miss_threshold,
        cooldown=providers.Callable(timedelta, days=config.provided.backoff_cooldown_days),
    )
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
        space_guard=space_guard,
        include_cutoff_unmet=config.provided.include_cutoff_unmet,
        fallback_per_day=config.provided.fallback_searches_per_day,
        prowlarr_fallback_on_error=config.provided.prowlarr_fallback_on_error,
        poll_interval_sec=config.provided.poll_interval_sec,
    )

    # Profile commands need neither the server Config nor the observer settings.
    profile_files = providers.Singleton(LocalProfileFiles)
    schemas = providers.Singleton(profile_schemas)
    profile_codec = providers.Singleton(YamlJsonCodec, schemas=schemas)
    profile_store = providers.Singleton(ProfileStore, files=profile_files, codec=profile_codec)
    profile_settings = providers.Singleton(ProfileSettings.from_env, env=environment)
    profile_selections = providers.Callable(
        lambda env: {source: env[f"WARDEN_{source.upper()}_PROFILES"] for source in ("radarr", "sonarr") if f"WARDEN_{source.upper()}_PROFILES" in env}, environment,
    )
    profile_cache = providers.Singleton(
        SnapshotCache, directory=profile_settings.provided.cache, max_bytes=profile_settings.provided.max_bytes,
    )
    git_client = providers.Singleton(
        GitClient, cache_directory=profile_settings.provided.cache, timeout=profile_settings.provided.timeout,
        check_budget=profile_cache.provided.check,
    )
    directory_profiles = providers.Singleton(
        DirectoryProfileSource, directory=profile_settings.provided.directory,
        store=profile_store, max_bytes=profile_settings.provided.max_bytes,
    )
    git_profiles = providers.Singleton(
        GitProfileSource, repo=profile_settings.provided.repo, ref=profile_settings.provided.ref,
        path=profile_settings.provided.path, git=git_client, cache=profile_cache, store=profile_store,
    )
    profile_source = providers.Selector(
        providers.Callable(lambda settings: "directory" if settings.directory else "git", profile_settings),
        directory=directory_profiles, git=git_profiles,
    )
    profile_emit = providers.Object(emit_profile_event)
    profile_observer = providers.Singleton(
        Observer, source=profile_source, arr=arr_service, selections=profile_selections,
        metrics=metrics, clock=clock, emit=profile_emit,
    )

    stop = providers.Singleton(asyncio.Event)
    app = providers.Singleton(FastAPI, title="Warden")
    web_app = providers.Singleton(create_app, app=app)
    server_config = providers.Singleton(
        uvicorn.Config, app=web_app, host="0.0.0.0", port=config.provided.metrics_port, log_level="info",
    )
    server = providers.Singleton(uvicorn.Server, config=server_config)
    hunt = providers.Callable(_hunt_loop, stop=stop, orchestrator=orchestrator)
    profile_loop = providers.Callable(
        run_profiles, stop=stop, arr=arr_service, metrics=metrics, clock=clock, env=environment,
        settings_factory=profile_settings.provider, observer_factory=profile_observer.provider, emit=profile_emit,
    )
    serve_command = providers.Callable(
        serve, cfg=config, server=server, stop=stop, hunt=hunt.provider, profiles=profile_loop.provider,
    )
