from __future__ import annotations

import asyncio
from argparse import Namespace
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest
from dependency_injector import providers

from warden.arr_service import ArrService
from warden.cli import build_parser, dispatch, diff_command, dump_command, serve_command, validate_command
from warden.container import Container
from warden.profiles.files import ProfileStore
from warden.profiles.models import ProfileDocument
from warden.cli_output import CommandOutput


@pytest.fixture()
def container() -> Iterator[Container]:
    container = Container()
    container.environment.override({})
    try:
        yield container
    finally:
        container.unwire()


async def test_validate_uses_injected_store_without_initializing_other_resources(container: Container) -> None:
    container.environment.override({"WARDEN_METRICS_PORT": "invalid", "WARDEN_PROFILES_REPO": "--invalid"})
    store = Mock(spec=ProfileStore)
    store.load.return_value = (ProfileDocument("radarr", "profiles", "hd.yml", {"quality_profiles": [{"name": "HD"}]}),)
    container.profile_store.override(store)
    result = await dispatch(build_parser().parse_args(["profiles", "validate", "--directory", "/profiles"]), container)
    assert result == CommandOutput("Valid configuration: 1 profiles, 0 custom formats.\n")
    store.load.assert_called_once_with(Path("/profiles"))
    assert not container.http.initialized


@pytest.mark.parametrize("failure", [False, True])
async def test_command_shuts_down_initialized_resources(container: Container, failure: bool) -> None:
    events: list[str] = []

    async def http_resource() -> AsyncIterator[object]:
        events.append("opened")
        try:
            yield object()
        finally:
            events.append("closed")

    container.http.override(providers.Resource(http_resource))
    await container.http()
    store = Mock(spec=ProfileStore)
    store.load.return_value = ()
    if failure:
        store.load.side_effect = ValueError("invalid profiles")
    container.profile_store.override(store)
    result = await dispatch(build_parser().parse_args(["profiles", "validate", "--directory", "/profiles"]), container)
    expected = CommandOutput(stderr="error: invalid profiles\n", exit_code=1) if failure else CommandOutput("Valid configuration: 0 profiles, 0 custom formats.\n")
    assert result == expected
    assert events == ["opened", "closed"]


async def test_cancelled_server_shuts_down_initialized_resources(container: Container) -> None:
    events: list[str] = []

    async def http_resource() -> AsyncIterator[object]:
        try:
            yield object()
        finally:
            events.append("closed")

    async def cancelled_server() -> None:
        raise asyncio.CancelledError()

    container.http.override(providers.Resource(http_resource))
    container.serve_command.override(providers.Callable(cancelled_server))
    await container.http()
    with pytest.raises(asyncio.CancelledError):
        await dispatch(build_parser().parse_args(["serve"]), container)
    assert events == ["closed"]


@pytest.mark.parametrize(("arguments", "handler"), [
    (["serve"], serve_command),
    (["profiles", "validate", "--directory", "/profiles"], validate_command),
    (["profiles", "dump", "--source", "radarr", "--output", "/profiles"], dump_command),
    (["profiles", "diff", "--source", "sonarr", "--directory", "/profiles"], diff_command),
])
def test_parser_selects_command_handler(arguments: list[str], handler: Callable[[Namespace], Awaitable[CommandOutput]]) -> None:
    assert build_parser().parse_args(arguments).func is handler


async def test_dispatch_executes_selected_handler(container: Container) -> None:
    calls = []

    async def handler(args: Namespace) -> CommandOutput:
        calls.append(args)
        return CommandOutput("selected handler\n", exit_code=2)

    args = Namespace(func=handler, command="custom")
    assert await dispatch(args, container) == CommandOutput("selected handler\n", exit_code=2)
    assert calls == [args]


async def test_serve_uses_injected_command(container: Container) -> None:
    calls = []

    async def run() -> None:
        calls.append("serve")

    container.serve_command.override(providers.Callable(run))
    args = build_parser().parse_args(["serve"])
    assert await dispatch(args, container) == CommandOutput()
    assert calls == ["serve"]
    assert not container.http.initialized


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_diff_handler_receives_store_arr_and_environment(container: Container, asynchronous: bool) -> None:
    store, arr = Mock(spec=ProfileStore), Mock(spec=ArrService)
    store.load.return_value = ()
    resolved = []

    async def provide_arr() -> ArrService:
        resolved.append("arr")
        return arr

    container.profile_store.override(store)
    container.arr_service.override(providers.Callable(provide_arr) if asynchronous else arr)
    container.environment.override({"WARDEN_RADARR_PROFILES": "[]"})
    args = build_parser().parse_args(["profiles", "diff", "--source", "radarr", "--directory", "/profiles"])
    assert await dispatch(args, container) == CommandOutput("radarr: profile comparison disabled.\n")
    store.load.assert_called_once_with(Path("/profiles"))
    arr.get_profiles.assert_not_called()
    assert resolved == (["arr"] if asynchronous else [])
    assert not container.http.initialized
