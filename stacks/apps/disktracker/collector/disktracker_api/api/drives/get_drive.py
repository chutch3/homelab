from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.drive import Drive
from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from typing import cast
from uuid import UUID



def _get_kwargs(
    drive_id: UUID,

) -> dict[str, Any]:






    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/drives/{drive_id}".format(drive_id=quote(str(drive_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Drive | ErrorResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = Drive.from_dict(response.json())



        return response_200

    if response.status_code == 404:
        response_404 = ErrorResponse.from_dict(response.json())



        return response_404

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Drive | ErrorResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Response[Drive | ErrorResponse | HTTPValidationError]:
    """ Get a drive

     A drive with every other MPN it goes by. Its offers are GET /offers?drive_id=; the range
    of its price in each condition is GET /reports/price-ranges.

    Args:
        drive_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Drive | ErrorResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        drive_id=drive_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Drive | ErrorResponse | HTTPValidationError | None:
    """ Get a drive

     A drive with every other MPN it goes by. Its offers are GET /offers?drive_id=; the range
    of its price in each condition is GET /reports/price-ranges.

    Args:
        drive_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Drive | ErrorResponse | HTTPValidationError
     """


    return sync_detailed(
        drive_id=drive_id,
client=client,

    ).parsed

async def asyncio_detailed(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Response[Drive | ErrorResponse | HTTPValidationError]:
    """ Get a drive

     A drive with every other MPN it goes by. Its offers are GET /offers?drive_id=; the range
    of its price in each condition is GET /reports/price-ranges.

    Args:
        drive_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Drive | ErrorResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        drive_id=drive_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Drive | ErrorResponse | HTTPValidationError | None:
    """ Get a drive

     A drive with every other MPN it goes by. Its offers are GET /offers?drive_id=; the range
    of its price in each condition is GET /reports/price-ranges.

    Args:
        drive_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Drive | ErrorResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        drive_id=drive_id,
client=client,

    )).parsed
