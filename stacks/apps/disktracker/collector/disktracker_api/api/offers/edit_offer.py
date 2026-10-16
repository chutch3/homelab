from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.offer import Offer
from ...models.offer_edit import OfferEdit
from typing import cast
from uuid import UUID



def _get_kwargs(
    offer_id: UUID,
    *,
    body: OfferEdit,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/offers/{offer_id}".format(offer_id=quote(str(offer_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ErrorResponse | HTTPValidationError | Offer | None:
    if response.status_code == 200:
        response_200 = Offer.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ErrorResponse | HTTPValidationError | Offer]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    offer_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: OfferEdit,

) -> Response[ErrorResponse | HTTPValidationError | Offer]:
    """ Edit offer details

     Change the supplied title or URL; omitted fields stay unchanged. A null URL clears it. MPN,
    store, seller and condition identify the offer and cannot be edited here.

    Args:
        offer_id (UUID):
        body (OfferEdit): Details that can change in place; MPN, store, seller and condition
            identify the offer.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | Offer]
     """


    kwargs = _get_kwargs(
        offer_id=offer_id,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    offer_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: OfferEdit,

) -> ErrorResponse | HTTPValidationError | Offer | None:
    """ Edit offer details

     Change the supplied title or URL; omitted fields stay unchanged. A null URL clears it. MPN,
    store, seller and condition identify the offer and cannot be edited here.

    Args:
        offer_id (UUID):
        body (OfferEdit): Details that can change in place; MPN, store, seller and condition
            identify the offer.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | Offer
     """


    return sync_detailed(
        offer_id=offer_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    offer_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: OfferEdit,

) -> Response[ErrorResponse | HTTPValidationError | Offer]:
    """ Edit offer details

     Change the supplied title or URL; omitted fields stay unchanged. A null URL clears it. MPN,
    store, seller and condition identify the offer and cannot be edited here.

    Args:
        offer_id (UUID):
        body (OfferEdit): Details that can change in place; MPN, store, seller and condition
            identify the offer.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | Offer]
     """


    kwargs = _get_kwargs(
        offer_id=offer_id,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    offer_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    body: OfferEdit,

) -> ErrorResponse | HTTPValidationError | Offer | None:
    """ Edit offer details

     Change the supplied title or URL; omitted fields stay unchanged. A null URL clears it. MPN,
    store, seller and condition identify the offer and cannot be edited here.

    Args:
        offer_id (UUID):
        body (OfferEdit): Details that can change in place; MPN, store, seller and condition
            identify the offer.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | Offer
     """


    return (await asyncio_detailed(
        offer_id=offer_id,
client=client,
body=body,

    )).parsed
