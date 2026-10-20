from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.merge_input import MergeInput
from ...models.merge_result import MergeResult
from typing import cast
from uuid import UUID



def _get_kwargs(
    source_id: UUID,
    *,
    body: MergeInput,
    idempotency_key: UUID,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["idempotency-key"] = idempotency_key







    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/drives/{source_id}/merge".format(source_id=quote(str(source_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ErrorResponse | HTTPValidationError | MergeResult | None:
    if response.status_code == 200:
        response_200 = MergeResult.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ErrorResponse | HTTPValidationError | MergeResult]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    source_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: MergeInput,
    idempotency_key: UUID,

) -> Response[ErrorResponse | HTTPValidationError | MergeResult]:
    """ Merge a drive into another

     Merge the drive into the target, which survives: with every MPN the drive went by (its
    own and its others), its brand where the target has none, its specifications where the
    target's are unknown, and its offers. An offer of the same store, seller and condition as
    one of the target's is combined into the target's: its prices are kept, it stays held if
    either was, and it was last checked when either was. Drives that both know a capacity or a
    specification and differ on it are not merged (409): correct one first. Sent again under the
    same Idempotency-Key it is answered as it was; the answer names the offers as they were.

    Args:
        source_id (UUID):
        idempotency_key (UUID): New UUID for each merge; sent again with the same body, it is
            answered as it was.
        body (MergeInput): The drive another is merged into: it survives.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | MergeResult]
     """


    kwargs = _get_kwargs(
        source_id=source_id,
body=body,
idempotency_key=idempotency_key,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    source_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: MergeInput,
    idempotency_key: UUID,

) -> ErrorResponse | HTTPValidationError | MergeResult | None:
    """ Merge a drive into another

     Merge the drive into the target, which survives: with every MPN the drive went by (its
    own and its others), its brand where the target has none, its specifications where the
    target's are unknown, and its offers. An offer of the same store, seller and condition as
    one of the target's is combined into the target's: its prices are kept, it stays held if
    either was, and it was last checked when either was. Drives that both know a capacity or a
    specification and differ on it are not merged (409): correct one first. Sent again under the
    same Idempotency-Key it is answered as it was; the answer names the offers as they were.

    Args:
        source_id (UUID):
        idempotency_key (UUID): New UUID for each merge; sent again with the same body, it is
            answered as it was.
        body (MergeInput): The drive another is merged into: it survives.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | MergeResult
     """


    return sync_detailed(
        source_id=source_id,
client=client,
body=body,
idempotency_key=idempotency_key,

    ).parsed

async def asyncio_detailed(
    source_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: MergeInput,
    idempotency_key: UUID,

) -> Response[ErrorResponse | HTTPValidationError | MergeResult]:
    """ Merge a drive into another

     Merge the drive into the target, which survives: with every MPN the drive went by (its
    own and its others), its brand where the target has none, its specifications where the
    target's are unknown, and its offers. An offer of the same store, seller and condition as
    one of the target's is combined into the target's: its prices are kept, it stays held if
    either was, and it was last checked when either was. Drives that both know a capacity or a
    specification and differ on it are not merged (409): correct one first. Sent again under the
    same Idempotency-Key it is answered as it was; the answer names the offers as they were.

    Args:
        source_id (UUID):
        idempotency_key (UUID): New UUID for each merge; sent again with the same body, it is
            answered as it was.
        body (MergeInput): The drive another is merged into: it survives.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | MergeResult]
     """


    kwargs = _get_kwargs(
        source_id=source_id,
body=body,
idempotency_key=idempotency_key,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    source_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: MergeInput,
    idempotency_key: UUID,

) -> ErrorResponse | HTTPValidationError | MergeResult | None:
    """ Merge a drive into another

     Merge the drive into the target, which survives: with every MPN the drive went by (its
    own and its others), its brand where the target has none, its specifications where the
    target's are unknown, and its offers. An offer of the same store, seller and condition as
    one of the target's is combined into the target's: its prices are kept, it stays held if
    either was, and it was last checked when either was. Drives that both know a capacity or a
    specification and differ on it are not merged (409): correct one first. Sent again under the
    same Idempotency-Key it is answered as it was; the answer names the offers as they were.

    Args:
        source_id (UUID):
        idempotency_key (UUID): New UUID for each merge; sent again with the same body, it is
            answered as it was.
        body (MergeInput): The drive another is merged into: it survives.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | MergeResult
     """


    return (await asyncio_detailed(
        source_id=source_id,
client=client,
body=body,
idempotency_key=idempotency_key,

    )).parsed
