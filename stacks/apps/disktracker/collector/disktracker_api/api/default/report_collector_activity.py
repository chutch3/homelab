from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.activity import Activity
from ...models.activity_answer import ActivityAnswer
from ...models.http_validation_error import HTTPValidationError
from typing import cast



def _get_kwargs(
    *,
    body: Activity,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/collector-activity",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ActivityAnswer | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ActivityAnswer.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ActivityAnswer | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: Activity,

) -> Response[ActivityAnswer | HTTPValidationError]:
    """ Report Collector Activity

    Args:
        body (Activity): How far a run in progress has got, as the collector says while it runs.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ActivityAnswer | HTTPValidationError]
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
    body: Activity,

) -> ActivityAnswer | HTTPValidationError | None:
    """ Report Collector Activity

    Args:
        body (Activity): How far a run in progress has got, as the collector says while it runs.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ActivityAnswer | HTTPValidationError
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: Activity,

) -> Response[ActivityAnswer | HTTPValidationError]:
    """ Report Collector Activity

    Args:
        body (Activity): How far a run in progress has got, as the collector says while it runs.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ActivityAnswer | HTTPValidationError]
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
    body: Activity,

) -> ActivityAnswer | HTTPValidationError | None:
    """ Report Collector Activity

    Args:
        body (Activity): How far a run in progress has got, as the collector says while it runs.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ActivityAnswer | HTTPValidationError
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
