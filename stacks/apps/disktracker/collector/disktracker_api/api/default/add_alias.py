from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.alias_input import AliasInput
from ...models.drive import Drive
from ...models.http_validation_error import HTTPValidationError
from typing import cast
from uuid import UUID



def _get_kwargs(
    drive_id: UUID,
    *,
    body: AliasInput,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/drives/{drive_id}/aliases".format(drive_id=quote(str(drive_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Drive | HTTPValidationError | None:
    if response.status_code == 201:
        response_201 = Drive.from_dict(response.json())



        return response_201

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Drive | HTTPValidationError]:
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
    body: AliasInput,

) -> Response[Drive | HTTPValidationError]:
    """ Add Alias

    Args:
        drive_id (UUID):
        body (AliasInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Drive | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        drive_id=drive_id,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: AliasInput,

) -> Drive | HTTPValidationError | None:
    """ Add Alias

    Args:
        drive_id (UUID):
        body (AliasInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Drive | HTTPValidationError
     """


    return sync_detailed(
        drive_id=drive_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: AliasInput,

) -> Response[Drive | HTTPValidationError]:
    """ Add Alias

    Args:
        drive_id (UUID):
        body (AliasInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Drive | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        drive_id=drive_id,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: AliasInput,

) -> Drive | HTTPValidationError | None:
    """ Add Alias

    Args:
        drive_id (UUID):
        body (AliasInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Drive | HTTPValidationError
     """


    return (await asyncio_detailed(
        drive_id=drive_id,
client=client,
body=body,

    )).parsed
