from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.offer_summary import OfferSummary
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    recent_days: int | Unset = 7,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    params["recent_days"] = recent_days


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/reports/rechecks",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[OfferSummary] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = OfferSummary.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[OfferSummary]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,

) -> Response[HTTPValidationError | list[OfferSummary]]:
    """ Read the offers entered by hand due a check

     Offers entered by hand and not checked within recent_days, longest unchecked first: a
    collected offer is the collector's to check.

    Args:
        recent_days (int | Unset):  Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[OfferSummary]]
     """


    kwargs = _get_kwargs(
        recent_days=recent_days,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,

) -> HTTPValidationError | list[OfferSummary] | None:
    """ Read the offers entered by hand due a check

     Offers entered by hand and not checked within recent_days, longest unchecked first: a
    collected offer is the collector's to check.

    Args:
        recent_days (int | Unset):  Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[OfferSummary]
     """


    return sync_detailed(
        client=client,
recent_days=recent_days,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,

) -> Response[HTTPValidationError | list[OfferSummary]]:
    """ Read the offers entered by hand due a check

     Offers entered by hand and not checked within recent_days, longest unchecked first: a
    collected offer is the collector's to check.

    Args:
        recent_days (int | Unset):  Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[OfferSummary]]
     """


    kwargs = _get_kwargs(
        recent_days=recent_days,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,

) -> HTTPValidationError | list[OfferSummary] | None:
    """ Read the offers entered by hand due a check

     Offers entered by hand and not checked within recent_days, longest unchecked first: a
    collected offer is the collector's to check.

    Args:
        recent_days (int | Unset):  Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[OfferSummary]
     """


    return (await asyncio_detailed(
        client=client,
recent_days=recent_days,

    )).parsed
