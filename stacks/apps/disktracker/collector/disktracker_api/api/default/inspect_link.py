from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.source_inspection import SourceInspection
from ...models.source_inspection_input import SourceInspectionInput
from typing import cast



def _get_kwargs(
    *,
    body: SourceInspectionInput,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/source-inspections",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | SourceInspection | None:
    if response.status_code == 200:
        response_200 = SourceInspection.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | SourceInspection]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: SourceInspectionInput,

) -> Response[HTTPValidationError | SourceInspection]:
    """ Inspect Link

     From a link to one product page of a store: the sources that would read the store,
    best first, each with the offer it reads from that page and what recording it would
    do. Nothing is kept.

    Args:
        body (SourceInspectionInput): A link to one product page of a store, to find out how the
            store would be read.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SourceInspection]
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
    body: SourceInspectionInput,

) -> HTTPValidationError | SourceInspection | None:
    """ Inspect Link

     From a link to one product page of a store: the sources that would read the store,
    best first, each with the offer it reads from that page and what recording it would
    do. Nothing is kept.

    Args:
        body (SourceInspectionInput): A link to one product page of a store, to find out how the
            store would be read.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SourceInspection
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: SourceInspectionInput,

) -> Response[HTTPValidationError | SourceInspection]:
    """ Inspect Link

     From a link to one product page of a store: the sources that would read the store,
    best first, each with the offer it reads from that page and what recording it would
    do. Nothing is kept.

    Args:
        body (SourceInspectionInput): A link to one product page of a store, to find out how the
            store would be read.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SourceInspection]
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
    body: SourceInspectionInput,

) -> HTTPValidationError | SourceInspection | None:
    """ Inspect Link

     From a link to one product page of a store: the sources that would read the store,
    best first, each with the offer it reads from that page and what recording it would
    do. Nothing is kept.

    Args:
        body (SourceInspectionInput): A link to one product page of a store, to find out how the
            store would be read.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SourceInspection
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
