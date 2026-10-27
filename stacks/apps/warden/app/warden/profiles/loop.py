from __future__ import annotations

import asyncio
import contextlib
import inspect
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from warden.arr_service import ArrService
from warden.clock import SystemClock
from warden.metrics import Metrics
from warden.profiles.observer import Observer
from warden.profiles.settings import ProfileSettings, parse_selection


async def run_profiles(
    stop: asyncio.Event, arr: ArrService, metrics: Metrics,
    clock: SystemClock, env: Mapping[str, str],
    settings_factory: Callable[[], ProfileSettings | None],
    observer_factory: Callable[[], Observer | Awaitable[Observer]],
    emit: Callable[[str, dict[str, Any]], None],
) -> None:
    active = []
    settings = None
    config_error = None
    try:
        settings = settings_factory()
    except ValueError as exc:
        config_error = str(exc)
    for name in arr.sources:
        raw = env.get(f"WARDEN_{name.upper()}_PROFILES")
        enabled = bool(env.get("WARDEN_PROFILES_REPO") or env.get("WARDEN_PROFILES_DIRECTORY"))
        try:
            enabled = enabled and parse_selection(raw) != []
        except ValueError:
            pass
        metrics.profile_enabled(name, enabled, settings.interval if settings else 900, clock.now().timestamp())
        if enabled:
            active.append(name)
    if config_error:
        emit("profile_config_error", {"reason": config_error})
    if settings is None or not active:
        return
    observer = observer_factory()
    if inspect.isawaitable(observer):
        observer = await observer
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
                    emit("profile_cycle_timeout", {})
                else:
                    await cycle
            except Exception as exc:
                for source in active:
                    metrics.profile_failed(source)
                emit("profile_cycle_error", {"error_type": type(exc).__name__})
            finally:
                cycle.cancel()
                await asyncio.gather(cycle, return_exceptions=True)
                metrics.profiles_duration.observe(time.monotonic() - started)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=settings.interval)
    finally:
        stopping.cancel()
        await asyncio.gather(stopping, return_exceptions=True)
