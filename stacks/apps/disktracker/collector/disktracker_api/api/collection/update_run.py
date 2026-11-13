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
from ...models.run_update import RunUpdate
from typing import cast
from uuid import UUID



def _get_kwargs(
    run_id: UUID,
    *,
    body: RunUpdate,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/collection-runs/{run_id}".format(run_id=quote(str(run_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ErrorResponse | HTTPValidationError | Run | None:
    if response.status_code == 200:
        response_200 = Run.from_dict(response.json())



        return response_200

    if response.status_code == 404:
        response_404 = ErrorResponse.from_dict(response.json())



        return response_404

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
    run_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: RunUpdate,

) -> Response[ErrorResponse | HTTPValidationError | Run]:
    """ Report progress or finish a collection run

     How far a run has got, or how it ended. The answer's stop_requested says whether it
    should end here. A run that has ended stays as it ended: the same end again is answered as
    before, and anything else is refused (409).

    Args:
        run_id (UUID):
        body (RunUpdate): How far a run has got, or how it ended: running with its counts so far,
            or completed,
            failed or stopped (asked to stop) with when it finished. Counts are what it has done in
            all,
            not since it last said.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | Run]
     """


    kwargs = _get_kwargs(
        run_id=run_id,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    run_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: RunUpdate,

) -> ErrorResponse | HTTPValidationError | Run | None:
    """ Report progress or finish a collection run

     How far a run has got, or how it ended. The answer's stop_requested says whether it
    should end here. A run that has ended stays as it ended: the same end again is answered as
    before, and anything else is refused (409).

    Args:
        run_id (UUID):
        body (RunUpdate): How far a run has got, or how it ended: running with its counts so far,
            or completed,
            failed or stopped (asked to stop) with when it finished. Counts are what it has done in
            all,
            not since it last said.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | Run
     """


    return sync_detailed(
        run_id=run_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    run_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: RunUpdate,

) -> Response[ErrorResponse | HTTPValidationError | Run]:
    """ Report progress or finish a collection run

     How far a run has got, or how it ended. The answer's stop_requested says whether it
    should end here. A run that has ended stays as it ended: the same end again is answered as
    before, and anything else is refused (409).

    Args:
        run_id (UUID):
        body (RunUpdate): How far a run has got, or how it ended: running with its counts so far,
            or completed,
            failed or stopped (asked to stop) with when it finished. Counts are what it has done in
            all,
            not since it last said.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | Run]
     """


    kwargs = _get_kwargs(
        run_id=run_id,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    run_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: RunUpdate,

) -> ErrorResponse | HTTPValidationError | Run | None:
    """ Report progress or finish a collection run

     How far a run has got, or how it ended. The answer's stop_requested says whether it
    should end here. A run that has ended stays as it ended: the same end again is answered as
    before, and anything else is refused (409).

    Args:
        run_id (UUID):
        body (RunUpdate): How far a run has got, or how it ended: running with its counts so far,
            or completed,
            failed or stopped (asked to stop) with when it finished. Counts are what it has done in
            all,
            not since it last said.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | Run
     """


    return (await asyncio_detailed(
        run_id=run_id,
client=client,
body=body,

    )).parsed
