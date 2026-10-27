from __future__ import annotations

import asyncio
from argparse import Namespace
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import Mock

import pytest
from dependency_injector import providers

from warden.cli import dispatch
from warden.container import Container
from warden.profiles.files import ProfileStore
from warden.profiles.models import ProfileDocument
from warden.profiles.presentation import CommandOutput


async def test_validate_uses_injected_store_without_initializing_other_resources() -> None:
    container = Container()
    container.environment.override({"WARDEN_METRICS_PORT": "invalid", "WARDEN_PROFILES_REPO": "--invalid"})
    store = Mock(spec=ProfileStore)
    store.load.return_value = (ProfileDocument("radarr", "profiles", "hd.yml", {"quality_profiles": [{"name": "HD"}]}),)
    container.profile_store.override(store)
    result = await dispatch(Namespace(group="profiles", command="validate", directory=Path("/profiles")), container)
    assert result == CommandOutput("Valid configuration: 1 profiles, 0 custom formats.\n")
    store.load.assert_called_once_with(Path("/profiles"))
    assert not container.http.initialized


@pytest.mark.parametrize("failure", [False, True])
async def test_command_shuts_down_initialized_resources(failure: bool) -> None:
    events: list[str] = []

    async def http_resource() -> AsyncIterator[object]:
        events.append("opened")
        try:
            yield object()
        finally:
            events.append("closed")

    container = Container()
    container.http.override(providers.Resource(http_resource))
    await container.http()
    store = Mock(spec=ProfileStore)
    store.load.return_value = ()
    if failure:
        store.load.side_effect = ValueError("invalid profiles")
    container.profile_store.override(store)
    result = await dispatch(Namespace(group="profiles", command="validate", directory=Path("/profiles")), container)
    expected = CommandOutput(stderr="error: invalid profiles\n", exit_code=1) if failure else CommandOutput("Valid configuration: 0 profiles, 0 custom formats.\n")
    assert result == expected
    assert events == ["opened", "closed"]


async def test_cancelled_server_shuts_down_initialized_resources() -> None:
    events: list[str] = []

    async def http_resource() -> AsyncIterator[object]:
        try:
            yield object()
        finally:
            events.append("closed")

    async def cancelled_server() -> None:
        raise asyncio.CancelledError()

    container = Container()
    container.http.override(providers.Resource(http_resource))
    container.serve_command.override(providers.Callable(cancelled_server))
    await container.http()
    with pytest.raises(asyncio.CancelledError):
        await dispatch(Namespace(group="serve"), container)
    assert events == ["closed"]
