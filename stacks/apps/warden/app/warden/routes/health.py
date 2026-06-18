from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Response
from prometheus_client import generate_latest

from warden.container import Container
from warden.metrics import Metrics

router = APIRouter()


@router.get("/metrics")
@inject
def metrics_endpoint(metrics: Metrics = Depends(Provide[Container.metrics])) -> Response:
    return Response(generate_latest(metrics.registry), media_type="text/plain")
