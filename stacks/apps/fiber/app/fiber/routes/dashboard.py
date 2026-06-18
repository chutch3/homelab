from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from fiber.clients.events import EventBroker
from fiber.clients.probe import ConnectivityProbe
from fiber.container import Container
from fiber.services.dashboard import DashboardService
from fiber.services.orchestrator import MovementOrchestrator
from fiber.services.registry_state import RegistryState
from fiber.services.worker_pool import WorkerPool
from fiber.status import DBStatus
from fiber.view import CardVM

_logger = logging.getLogger(__name__)


def tiles_to_push(cards: list[CardVM], signalled: str | None) -> list[str]:
    """Return the list of service names to push in an SSE cycle.

    If *signalled* is given, push only that service (broker-triggered update).
    Otherwise push only the straining services (2s timeout tick).
    """
    if signalled is not None:
        return [signalled]
    return [c.service for c in cards if c.status is DBStatus.STRAINING]

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@inject
async def wall(
    request: Request,
    svc: DashboardService = Depends(Provide[Container.dashboard_service]),
    templates: Jinja2Templates = Depends(Provide[Container.templates]),
) -> HTMLResponse:
    vm = svc.build()
    return templates.TemplateResponse(request, "wall.html", {"vm": vm})


@router.get("/db/{service}", response_class=HTMLResponse)
@inject
async def drawer(
    service: str,
    request: Request,
    svc: DashboardService = Depends(Provide[Container.dashboard_service]),
    templates: Jinja2Templates = Depends(Provide[Container.templates]),
) -> HTMLResponse:
    d = svc.detail(service)
    return templates.TemplateResponse(request, "_drawer.html", {"d": d})


@router.post("/db/{service}/flush", response_class=HTMLResponse)
@inject
async def flush(
    service: str,
    request: Request,
    svc: DashboardService = Depends(Provide[Container.dashboard_service]),
    pool: WorkerPool = Depends(Provide[Container.pool]),
    orchestrator: MovementOrchestrator = Depends(Provide[Container.orchestrator]),
    registry_state: RegistryState = Depends(Provide[Container.registry_state]),
    templates: Jinja2Templates = Depends(Provide[Container.templates]),
) -> HTMLResponse:
    snap = registry_state.get()
    job = next((j for j in snap.jobs if j.service == service), None)
    if job is not None:
        pool.submit(service, lambda j=job: orchestrator.perform(j))
    c = svc.card(service)
    return templates.TemplateResponse(request, "_tile.html", {"c": c})


@router.post("/db/{service}/pinch", response_class=HTMLResponse)
@inject
async def pinch(
    service: str,
    request: Request,
    svc: DashboardService = Depends(Provide[Container.dashboard_service]),
    pool: WorkerPool = Depends(Provide[Container.pool]),
    templates: Jinja2Templates = Depends(Provide[Container.templates]),
) -> HTMLResponse:
    pool.cancel(service)
    c = svc.card(service)
    return templates.TemplateResponse(request, "_tile.html", {"c": c})


@router.post("/flush-all", response_class=HTMLResponse)
@inject
async def flush_all(
    request: Request,
    svc: DashboardService = Depends(Provide[Container.dashboard_service]),
    pool: WorkerPool = Depends(Provide[Container.pool]),
    orchestrator: MovementOrchestrator = Depends(Provide[Container.orchestrator]),
    registry_state: RegistryState = Depends(Provide[Container.registry_state]),
    templates: Jinja2Templates = Depends(Provide[Container.templates]),
) -> HTMLResponse:
    snap = registry_state.get()
    for job in snap.jobs:
        pool.submit(job.service, lambda j=job: orchestrator.perform(j))
    vm = svc.build()
    return templates.TemplateResponse(request, "_summary.html", {"vm": vm})


@router.get("/discovery", response_class=HTMLResponse)
@inject
async def discovery(
    request: Request,
    svc: DashboardService = Depends(Provide[Container.dashboard_service]),
    templates: Jinja2Templates = Depends(Provide[Container.templates]),
) -> HTMLResponse:
    vm = svc.build()
    return templates.TemplateResponse(request, "_discovery.html", {"rows": vm.discovery})


@router.post("/db/{service}/test", response_class=HTMLResponse)
@inject
async def test_connection(
    service: str,
    request: Request,
    probe: ConnectivityProbe = Depends(Provide[Container.probe]),
    registry_state: RegistryState = Depends(Provide[Container.registry_state]),
    templates: Jinja2Templates = Depends(Provide[Container.templates]),
) -> HTMLResponse:
    snap = registry_state.get()
    job = next((j for j in snap.jobs if j.service == service), None)
    if job is None:
        return HTMLResponse(content="<span>service not found</span>", status_code=404)
    result = await probe.check(job)
    return templates.TemplateResponse(
        request, "_probe_result.html", {"ok": result.ok, "detail": result.detail}
    )


@router.get("/events")
@inject
async def events(
    request: Request,
    svc: DashboardService = Depends(Provide[Container.dashboard_service]),
    broker: EventBroker = Depends(Provide[Container.events]),
    templates: Jinja2Templates = Depends(Provide[Container.templates]),
) -> EventSourceResponse:
    async def _stream() -> AsyncIterator[dict[str, str]]:
        q = broker.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    signalled: str | None = await asyncio.wait_for(q.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    signalled = None

                vm = svc.build()
                # push updated summary
                summary_html = templates.get_template("_summary.html").render({"vm": vm})
                yield {"data": json.dumps({"type": "summary", "html": summary_html})}

                # push only relevant tiles
                for svc_name in tiles_to_push(vm.cards, signalled):
                    card = next((c for c in vm.cards if c.service == svc_name), None)
                    if card is not None:
                        tile_html = templates.get_template("_tile.html").render({"c": card})
                        yield {"data": json.dumps({"type": "tile", "service": svc_name, "html": tile_html})}
        finally:
            broker.unsubscribe(q)

    return EventSourceResponse(_stream())
