from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.manual_source_view import ManualSourceView
from ...models.sap_commerce_source_view import SapCommerceSourceView
from ...models.shopify_source_view import ShopifySourceView
from ...models.sitemap_source_view import SitemapSourceView
from typing import cast
from uuid import UUID



def _get_kwargs(
    source_id: UUID,

) -> dict[str, Any]:






    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/sources/{source_id}/run".format(source_id=quote(str(source_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView | None:
    if response.status_code == 202:
        def _parse_response_202(data: object) -> ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_202_type_0 = ManualSourceView.from_dict(data)



                return response_202_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_202_type_1 = ShopifySourceView.from_dict(data)



                return response_202_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_202_type_2 = SitemapSourceView.from_dict(data)



                return response_202_type_2
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_202_type_3 = SapCommerceSourceView.from_dict(data)



            return response_202_type_3

        response_202 = _parse_response_202(response.json())

        return response_202

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]:
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

) -> Response[ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]:
    """ Schedule a source to run now

     Make the source due now until a collector registers its run. A 202 response acknowledges
    scheduling; collection has not necessarily started.

    Args:
        source_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]
     """


    kwargs = _get_kwargs(
        source_id=source_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    source_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView | None:
    """ Schedule a source to run now

     Make the source due now until a collector registers its run. A 202 response acknowledges
    scheduling; collection has not necessarily started.

    Args:
        source_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView
     """


    return sync_detailed(
        source_id=source_id,
client=client,

    ).parsed

async def asyncio_detailed(
    source_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Response[ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]:
    """ Schedule a source to run now

     Make the source due now until a collector registers its run. A 202 response acknowledges
    scheduling; collection has not necessarily started.

    Args:
        source_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]
     """


    kwargs = _get_kwargs(
        source_id=source_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    source_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView | None:
    """ Schedule a source to run now

     Make the source due now until a collector registers its run. A 202 response acknowledges
    scheduling; collection has not necessarily started.

    Args:
        source_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView
     """


    return (await asyncio_detailed(
        source_id=source_id,
client=client,

    )).parsed
