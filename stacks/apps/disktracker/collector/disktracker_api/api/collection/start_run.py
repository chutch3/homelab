from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.run import Run
from ...models.run_start import RunStart
from typing import cast



def _get_kwargs(
    *,
    body: RunStart,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/collection-runs",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ErrorResponse | HTTPValidationError | Run | None:
    if response.status_code == 200:
        response_200 = Run.from_dict(response.json())



        return response_200

    if response.status_code == 201:
        response_201 = Run.from_dict(response.json())



        return response_201

    if response.status_code == 409:
        response_409 = ErrorResponse.from_dict(response.json())



        return response_409

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ErrorResponse | HTTPValidationError | Run]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: RunStart,

) -> Response[ErrorResponse | HTTPValidationError | Run]:
    """ Register a collection run

     Register a run as it starts, under the id the collector chose: the same start sent again
    is answered with the run (200), and another under its id is refused (409). A run of the
    source still marked running is abandoned.

    Args:
        body (RunStart): A run as it starts. id: chosen by the collector, so a start whose answer
            was lost can be
            sent again.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | Run]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    body: RunStart,

) -> ErrorResponse | HTTPValidationError | Run | None:
    """ Register a collection run

     Register a run as it starts, under the id the collector chose: the same start sent again
    is answered with the run (200), and another under its id is refused (409). A run of the
    source still marked running is abandoned.

    Args:
        body (RunStart): A run as it starts. id: chosen by the collector, so a start whose answer
            was lost can be
            sent again.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | Run
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: RunStart,

) -> Response[ErrorResponse | HTTPValidationError | Run]:
    """ Register a collection run

     Register a run as it starts, under the id the collector chose: the same start sent again
    is answered with the run (200), and another under its id is refused (409). A run of the
    source still marked running is abandoned.

    Args:
        body (RunStart): A run as it starts. id: chosen by the collector, so a start whose answer
            was lost can be
            sent again.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | Run]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: RunStart,

) -> ErrorResponse | HTTPValidationError | Run | None:
    """ Register a collection run

     Register a run as it starts, under the id the collector chose: the same start sent again
    is answered with the run (200), and another under its id is refused (409). A run of the
    source still marked running is abandoned.

    Args:
        body (RunStart): A run as it starts. id: chosen by the collector, so a start whose answer
            was lost can be
            sent again.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | Run
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
