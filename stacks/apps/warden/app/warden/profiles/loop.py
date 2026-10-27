from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Mapping, Sequence
from typing import Any

from warden.clients.arr import ArrClient
from warden.clock import SystemClock
from warden.logger import get_logger
from warden.metrics import Metrics
from warden.arr_service import ArrService
from warden.clients.git import GitClient
from warden.profiles.cache import SnapshotCache
from warden.profiles.codec import profile_codec
from warden.profiles.files import ProfileStore, LocalProfileFiles
from warden.profiles.sources import DirectoryProfileSource, GitProfileSource, ProfileSource
from warden.profiles.observer import Observer
from warden.profiles.settings import ProfileSettings, parse_selection


def _emit(event: str, fields: dict[str, Any]) -> None:
    get_logger("warden.profiles").info(event, extra={"event": event, **fields})


async def run_profiles(
    stop: asyncio.Event, clients: Sequence[ArrClient], metrics: Metrics,
    clock: SystemClock, env: Mapping[str, str],
) -> None:
    active = []
    selections = {}
    settings = None
    config_error = None
    try:
        settings = ProfileSettings.from_env(env)
    except ValueError as exc:
        config_error = str(exc)
    for client in clients:
        raw = env.get(f"WARDEN_{client.name.upper()}_PROFILES")
        if raw is not None:
            selections[client.name] = raw
        enabled = bool(env.get("WARDEN_PROFILES_REPO") or env.get("WARDEN_PROFILES_DIRECTORY"))
        try:
            enabled = enabled and parse_selection(raw) != []
        except ValueError:
            pass
        metrics.profile_enabled(client.name, enabled, settings.interval if settings else 900, clock.now().timestamp())
        if enabled:
            active.append(client.name)
    if config_error:
        _emit("profile_config_error", {"reason": config_error})
    if settings is None or not active:
        return
    store = ProfileStore(LocalProfileFiles(), profile_codec())
    source: ProfileSource
    if settings.directory:
        source = DirectoryProfileSource(settings.directory, store, settings.max_bytes)
    else:
        cache = SnapshotCache(settings.cache, settings.max_bytes)
        git = GitClient(settings.cache, settings.timeout, cache.check)
        source = GitProfileSource(settings.repo, settings.ref, settings.path, git, cache, store)
    arr = ArrService({client.name: client for client in clients})
    observer = Observer(source, arr, selections, metrics, clock, _emit)
    stopping = asyncio.create_task(stop.wait())
    try:
        while not stop.is_set():
            started = time.monotonic()
            cycle = asyncio.create_task(observer.tick())
            try:
                done, _ = await asyncio.wait({cycle, stopping}, timeout=settings.timeout, return_when=asyncio.FIRST_COMPLETED)
                if stopping in done:
                    break
                if cycle not in done:
                    for source in active:
                        metrics.profile_failed(source)
                    _emit("profile_cycle_timeout", {})
                else:
                    await cycle
            except Exception as exc:
                for source in active:
                    metrics.profile_failed(source)
                _emit("profile_cycle_error", {"error_type": type(exc).__name__})
            finally:
                cycle.cancel()
                await asyncio.gather(cycle, return_exceptions=True)
                metrics.profiles_duration.observe(time.monotonic() - started)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=settings.interval)
    finally:
        stopping.cancel()
        await asyncio.gather(stopping, return_exceptions=True)
