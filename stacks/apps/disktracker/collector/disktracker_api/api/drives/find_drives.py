from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.found_drives import FoundDrives
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    mpn: None | str | Unset = UNSET,
    q: str | Unset = '',
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    json_mpn: None | str | Unset
    if isinstance(mpn, Unset):
        json_mpn = UNSET
    else:
        json_mpn = mpn
    params["mpn"] = json_mpn

    params["q"] = q

    params["limit"] = limit

    params["offset"] = offset


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/drives",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> FoundDrives | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = FoundDrives.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[FoundDrives | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    mpn: None | str | Unset = UNSET,
    q: str | Unset = '',
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> Response[FoundDrives | HTTPValidationError]:
    """ Find drives by MPN or words

     The drive that goes by an MPN (mpn, as its own or another of its MPNs; at most one), or
    the drives any name of which has some words (q): its MPN, another of its MPNs, or any name an
    offer of it goes by, held offers too; those the words are an MPN of first. Each is named by
    the title of its cheapest offer in stock, else its cheapest offer, else its MPN.

    Args:
        mpn (None | str | Unset):
        q (str | Unset):  Default: ''.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of drives found to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[FoundDrives | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        mpn=mpn,
q=q,
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
    mpn: None | str | Unset = UNSET,
    q: str | Unset = '',
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> FoundDrives | HTTPValidationError | None:
    """ Find drives by MPN or words

     The drive that goes by an MPN (mpn, as its own or another of its MPNs; at most one), or
    the drives any name of which has some words (q): its MPN, another of its MPNs, or any name an
    offer of it goes by, held offers too; those the words are an MPN of first. Each is named by
    the title of its cheapest offer in stock, else its cheapest offer, else its MPN.

    Args:
        mpn (None | str | Unset):
        q (str | Unset):  Default: ''.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of drives found to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        FoundDrives | HTTPValidationError
     """


    return sync_detailed(
        client=client,
mpn=mpn,
q=q,
limit=limit,
offset=offset,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    mpn: None | str | Unset = UNSET,
    q: str | Unset = '',
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> Response[FoundDrives | HTTPValidationError]:
    """ Find drives by MPN or words

     The drive that goes by an MPN (mpn, as its own or another of its MPNs; at most one), or
    the drives any name of which has some words (q): its MPN, another of its MPNs, or any name an
    offer of it goes by, held offers too; those the words are an MPN of first. Each is named by
    the title of its cheapest offer in stock, else its cheapest offer, else its MPN.

    Args:
        mpn (None | str | Unset):
        q (str | Unset):  Default: ''.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of drives found to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[FoundDrives | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        mpn=mpn,
q=q,
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
    mpn: None | str | Unset = UNSET,
    q: str | Unset = '',
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> FoundDrives | HTTPValidationError | None:
    """ Find drives by MPN or words

     The drive that goes by an MPN (mpn, as its own or another of its MPNs; at most one), or
    the drives any name of which has some words (q): its MPN, another of its MPNs, or any name an
    offer of it goes by, held offers too; those the words are an MPN of first. Each is named by
    the title of its cheapest offer in stock, else its cheapest offer, else its MPN.

    Args:
        mpn (None | str | Unset):
        q (str | Unset):  Default: ''.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of drives found to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        FoundDrives | HTTPValidationError
     """


    return (await asyncio_detailed(
        client=client,
mpn=mpn,
q=q,
limit=limit,
offset=offset,

    )).parsed
