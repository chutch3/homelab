from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.drive import Drive
from ...models.drive_input import DriveInput
from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from typing import cast



def _get_kwargs(
    *,
    body: DriveInput,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/drives",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Drive | ErrorResponse | HTTPValidationError | None:
    if response.status_code == 201:
        response_201 = Drive.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Drive | ErrorResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: DriveInput,

) -> Response[Drive | ErrorResponse | HTTPValidationError]:
    """ Make a drive

     Make a drive before any price of it, under an MPN that no drive goes by, as its own MPN or
    another of its MPNs. A drive already going by it is never merged with this one.

    Args:
        body (DriveInput): A drive made on its own, before any price of it: its MPN, which no
            drive may go by already,
            its capacity, and what is known of it. Specifications left out are unknown.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Drive | ErrorResponse | HTTPValidationError]
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
    body: DriveInput,

) -> Drive | ErrorResponse | HTTPValidationError | None:
    """ Make a drive

     Make a drive before any price of it, under an MPN that no drive goes by, as its own MPN or
    another of its MPNs. A drive already going by it is never merged with this one.

    Args:
        body (DriveInput): A drive made on its own, before any price of it: its MPN, which no
            drive may go by already,
            its capacity, and what is known of it. Specifications left out are unknown.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Drive | ErrorResponse | HTTPValidationError
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: DriveInput,

) -> Response[Drive | ErrorResponse | HTTPValidationError]:
    """ Make a drive

     Make a drive before any price of it, under an MPN that no drive goes by, as its own MPN or
    another of its MPNs. A drive already going by it is never merged with this one.

    Args:
        body (DriveInput): A drive made on its own, before any price of it: its MPN, which no
            drive may go by already,
            its capacity, and what is known of it. Specifications left out are unknown.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Drive | ErrorResponse | HTTPValidationError]
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
    body: DriveInput,

) -> Drive | ErrorResponse | HTTPValidationError | None:
    """ Make a drive

     Make a drive before any price of it, under an MPN that no drive goes by, as its own MPN or
    another of its MPNs. A drive already going by it is never merged with this one.

    Args:
        body (DriveInput): A drive made on its own, before any price of it: its MPN, which no
            drive may go by already,
            its capacity, and what is known of it. Specifications left out are unknown.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Drive | ErrorResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
