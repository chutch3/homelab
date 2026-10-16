from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.decision_result import DecisionResult
from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.ignore_decision import IgnoreDecision
from ...models.match_decision import MatchDecision
from typing import cast
from uuid import UUID



def _get_kwargs(
    item_id: UUID,
    *,
    body: IgnoreDecision | MatchDecision,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/review-items/{item_id}/decision".format(item_id=quote(str(item_id), safe=""),),
    }


    if isinstance(body, MatchDecision):
        _kwargs["json"] = body.to_dict()
    else:
        _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> DecisionResult | ErrorResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = DecisionResult.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[DecisionResult | ErrorResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    item_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: IgnoreDecision | MatchDecision,

) -> Response[DecisionResult | ErrorResponse | HTTPValidationError]:
    """ Match or ignore a review item

     Say what a review item is. Sent again, the same decision gets the first answer without
    doing anything more, so a decision whose answer was lost can be retried; a different decision
    is refused (409).

    Args:
        item_id (UUID):
        body (IgnoreDecision | MatchDecision):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DecisionResult | ErrorResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        item_id=item_id,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    item_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: IgnoreDecision | MatchDecision,

) -> DecisionResult | ErrorResponse | HTTPValidationError | None:
    """ Match or ignore a review item

     Say what a review item is. Sent again, the same decision gets the first answer without
    doing anything more, so a decision whose answer was lost can be retried; a different decision
    is refused (409).

    Args:
        item_id (UUID):
        body (IgnoreDecision | MatchDecision):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DecisionResult | ErrorResponse | HTTPValidationError
     """


    return sync_detailed(
        item_id=item_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    item_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: IgnoreDecision | MatchDecision,

) -> Response[DecisionResult | ErrorResponse | HTTPValidationError]:
    """ Match or ignore a review item

     Say what a review item is. Sent again, the same decision gets the first answer without
    doing anything more, so a decision whose answer was lost can be retried; a different decision
    is refused (409).

    Args:
        item_id (UUID):
        body (IgnoreDecision | MatchDecision):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DecisionResult | ErrorResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        item_id=item_id,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    item_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: IgnoreDecision | MatchDecision,

) -> DecisionResult | ErrorResponse | HTTPValidationError | None:
    """ Match or ignore a review item

     Say what a review item is. Sent again, the same decision gets the first answer without
    doing anything more, so a decision whose answer was lost can be retried; a different decision
    is refused (409).

    Args:
        item_id (UUID):
        body (IgnoreDecision | MatchDecision):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DecisionResult | ErrorResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        item_id=item_id,
client=client,
body=body,

    )).parsed
