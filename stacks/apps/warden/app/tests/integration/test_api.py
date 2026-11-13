from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from tests.integration.conftest import WardenHandle

pytestmark = pytest.mark.integration


def test_healthz_ok(launch: Callable[..., WardenHandle]) -> None:
    handle = launch()
    resp = httpx.get(f"{handle.base_url}/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_metrics_exposes_prometheus(launch: Callable[..., WardenHandle]) -> None:
    handle = launch()
    resp = httpx.get(f"{handle.base_url}/metrics")
    assert resp.status_code == 200
    assert "warden_daily_budget" in resp.text
