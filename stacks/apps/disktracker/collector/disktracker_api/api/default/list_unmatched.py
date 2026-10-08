from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.list_unmatched_reason_type_0 import check_list_unmatched_reason_type_0
from ...models.list_unmatched_reason_type_0 import ListUnmatchedReasonType0
from ...models.unmatched import Unmatched
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    source: None | str | Unset = UNSET,
    reason: ListUnmatchedReasonType0 | None | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    json_source: None | str | Unset
    if isinstance(source, Unset):
        json_source = UNSET
    else:
        json_source = source
    params["source"] = json_source

    json_reason: None | str | Unset
    if isinstance(reason, Unset):
        json_reason = UNSET
    elif isinstance(reason, str):
        json_reason = reason
    else:
        json_reason = reason
    params["reason"] = json_reason

    json_limit: int | None | Unset
    if isinstance(limit, Unset):
        json_limit = UNSET
    else:
        json_limit = limit
    params["limit"] = json_limit

    params["offset"] = offset


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/unmatched",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[Unmatched] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = Unmatched.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[Unmatched]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    reason: ListUnmatchedReasonType0 | None | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> Response[HTTPValidationError | list[Unmatched]]:
    """ List Unmatched

     The Review queue, newest first; by source and reason, and a part at a time, when
    asked. X-Total-Count says how many there are in all, whatever the limit.

    Args:
        source (None | str | Unset):
        reason (ListUnmatchedReasonType0 | None | Unset):
        limit (int | None | Unset):
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[Unmatched]]
     """


    kwargs = _get_kwargs(
        source=source,
reason=reason,
limit=limit,
offset=offset,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    reason: ListUnmatchedReasonType0 | None | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> HTTPValidationError | list[Unmatched] | None:
    """ List Unmatched

     The Review queue, newest first; by source and reason, and a part at a time, when
    asked. X-Total-Count says how many there are in all, whatever the limit.

    Args:
        source (None | str | Unset):
        reason (ListUnmatchedReasonType0 | None | Unset):
        limit (int | None | Unset):
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[Unmatched]
     """


    return sync_detailed(
        client=client,
source=source,
reason=reason,
limit=limit,
offset=offset,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    reason: ListUnmatchedReasonType0 | None | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> Response[HTTPValidationError | list[Unmatched]]:
    """ List Unmatched

     The Review queue, newest first; by source and reason, and a part at a time, when
    asked. X-Total-Count says how many there are in all, whatever the limit.

    Args:
        source (None | str | Unset):
        reason (ListUnmatchedReasonType0 | None | Unset):
        limit (int | None | Unset):
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[Unmatched]]
     """


    kwargs = _get_kwargs(
        source=source,
reason=reason,
limit=limit,
offset=offset,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    reason: ListUnmatchedReasonType0 | None | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> HTTPValidationError | list[Unmatched] | None:
    """ List Unmatched

     The Review queue, newest first; by source and reason, and a part at a time, when
    asked. X-Total-Count says how many there are in all, whatever the limit.

    Args:
        source (None | str | Unset):
        reason (ListUnmatchedReasonType0 | None | Unset):
        limit (int | None | Unset):
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[Unmatched]
     """


    return (await asyncio_detailed(
        client=client,
source=source,
reason=reason,
limit=limit,
offset=offset,

    )).parsed
