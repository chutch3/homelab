from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.alias_input import AliasInput
from ...models.drive import Drive
from ...models.error_response import ErrorResponse
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



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Drive | ErrorResponse | HTTPValidationError | None:
    if response.status_code == 201:
        response_201 = Drive.from_dict(response.json())



        return response_201

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
    body: AliasInput,

) -> Response[Drive | ErrorResponse | HTTPValidationError]:
    """ Add an alternate MPN or merge drives

     Declare another MPN for this drive. If it is another drive's canonical MPN, merge that
    drive's offers, price history and aliases into this drive, retaining this drive's capacity
    and specifications. Matching offers combine their histories. The target's own canonical
    MPN or an already registered alias returns 409.

    Args:
        drive_id (UUID):
        body (AliasInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Drive | ErrorResponse | HTTPValidationError]
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

) -> Drive | ErrorResponse | HTTPValidationError | None:
    """ Add an alternate MPN or merge drives

     Declare another MPN for this drive. If it is another drive's canonical MPN, merge that
    drive's offers, price history and aliases into this drive, retaining this drive's capacity
    and specifications. Matching offers combine their histories. The target's own canonical
    MPN or an already registered alias returns 409.

    Args:
        drive_id (UUID):
        body (AliasInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Drive | ErrorResponse | HTTPValidationError
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

) -> Response[Drive | ErrorResponse | HTTPValidationError]:
    """ Add an alternate MPN or merge drives

     Declare another MPN for this drive. If it is another drive's canonical MPN, merge that
    drive's offers, price history and aliases into this drive, retaining this drive's capacity
    and specifications. Matching offers combine their histories. The target's own canonical
    MPN or an already registered alias returns 409.

    Args:
        drive_id (UUID):
        body (AliasInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Drive | ErrorResponse | HTTPValidationError]
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

) -> Drive | ErrorResponse | HTTPValidationError | None:
    """ Add an alternate MPN or merge drives

     Declare another MPN for this drive. If it is another drive's canonical MPN, merge that
    drive's offers, price history and aliases into this drive, retaining this drive's capacity
    and specifications. Matching offers combine their histories. The target's own canonical
    MPN or an already registered alias returns 409.

    Args:
        drive_id (UUID):
        body (AliasInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Drive | ErrorResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        drive_id=drive_id,
client=client,
body=body,

    )).parsed
