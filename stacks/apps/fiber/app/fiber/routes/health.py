from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Response
from prometheus_client import generate_latest

from fiber.container import Container
from fiber.metrics import Metrics
from fiber.services.readiness import Readiness

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
@inject
def readyz(readiness: Readiness = Depends(Provide[Container.readiness])) -> Response:
    try:
        ok = readiness()
    except Exception:
        ok = False
    return Response(status_code=200 if ok else 503)


@router.get("/metrics")
@inject
def metrics_endpoint(metrics: Metrics = Depends(Provide[Container.metrics])) -> Response:
    return Response(generate_latest(metrics.registry), media_type="text/plain")
