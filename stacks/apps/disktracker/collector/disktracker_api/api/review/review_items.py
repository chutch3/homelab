from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.review_item import ReviewItem
from ...models.review_items_reason_type_0 import check_review_items_reason_type_0
from ...models.review_items_reason_type_0 import ReviewItemsReasonType0
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    store: None | str | Unset = UNSET,
    reason: None | ReviewItemsReasonType0 | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    json_store: None | str | Unset
    if isinstance(store, Unset):
        json_store = UNSET
    else:
        json_store = store
    params["store"] = json_store

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
        "url": "/api/review-items",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[ReviewItem] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = ReviewItem.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[ReviewItem]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    store: None | str | Unset = UNSET,
    reason: None | ReviewItemsReasonType0 | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> Response[HTTPValidationError | list[ReviewItem]]:
    """ List offers waiting for review

     The offers waiting for review, newest first; by store and reason, and a part at a time,
    when asked. X-Total-Count says how many there are in all, whatever the limit.

    Args:
        store (None | str | Unset):
        reason (None | ReviewItemsReasonType0 | Unset):
        limit (int | None | Unset): Maximum items; omit to return all remaining matches.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[ReviewItem]]
     """


    kwargs = _get_kwargs(
        store=store,
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
    store: None | str | Unset = UNSET,
    reason: None | ReviewItemsReasonType0 | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> HTTPValidationError | list[ReviewItem] | None:
    """ List offers waiting for review

     The offers waiting for review, newest first; by store and reason, and a part at a time,
    when asked. X-Total-Count says how many there are in all, whatever the limit.

    Args:
        store (None | str | Unset):
        reason (None | ReviewItemsReasonType0 | Unset):
        limit (int | None | Unset): Maximum items; omit to return all remaining matches.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[ReviewItem]
     """


    return sync_detailed(
        client=client,
store=store,
reason=reason,
limit=limit,
offset=offset,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    store: None | str | Unset = UNSET,
    reason: None | ReviewItemsReasonType0 | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> Response[HTTPValidationError | list[ReviewItem]]:
    """ List offers waiting for review

     The offers waiting for review, newest first; by store and reason, and a part at a time,
    when asked. X-Total-Count says how many there are in all, whatever the limit.

    Args:
        store (None | str | Unset):
        reason (None | ReviewItemsReasonType0 | Unset):
        limit (int | None | Unset): Maximum items; omit to return all remaining matches.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[ReviewItem]]
     """


    kwargs = _get_kwargs(
        store=store,
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
    store: None | str | Unset = UNSET,
    reason: None | ReviewItemsReasonType0 | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> HTTPValidationError | list[ReviewItem] | None:
    """ List offers waiting for review

     The offers waiting for review, newest first; by store and reason, and a part at a time,
    when asked. X-Total-Count says how many there are in all, whatever the limit.

    Args:
        store (None | str | Unset):
        reason (None | ReviewItemsReasonType0 | Unset):
        limit (int | None | Unset): Maximum items; omit to return all remaining matches.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[ReviewItem]
     """


    return (await asyncio_detailed(
        client=client,
store=store,
reason=reason,
limit=limit,
offset=offset,

    )).parsed
