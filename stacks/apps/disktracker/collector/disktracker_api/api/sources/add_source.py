from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.manual_source_input import ManualSourceInput
from ...models.manual_source_view import ManualSourceView
from ...models.sap_commerce_source_input import SapCommerceSourceInput
from ...models.sap_commerce_source_view import SapCommerceSourceView
from ...models.shopify_source_input import ShopifySourceInput
from ...models.shopify_source_view import ShopifySourceView
from ...models.sitemap_source_input import SitemapSourceInput
from ...models.sitemap_source_view import SitemapSourceView
from typing import cast



def _get_kwargs(
    *,
    body: ManualSourceInput | SapCommerceSourceInput | ShopifySourceInput | SitemapSourceInput,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/sources",
    }


    if isinstance(body, ManualSourceInput):
        _kwargs["json"] = body.to_dict()
    elif isinstance(body, ShopifySourceInput):
        _kwargs["json"] = body.to_dict()
    elif isinstance(body, SitemapSourceInput):
        _kwargs["json"] = body.to_dict()
    else:
        _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView | None:
    if response.status_code == 201:
        def _parse_response_201(data: object) -> ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_201_type_0 = ManualSourceView.from_dict(data)



                return response_201_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_201_type_1 = ShopifySourceView.from_dict(data)



                return response_201_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_201_type_2 = SitemapSourceView.from_dict(data)



                return response_201_type_2
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_201_type_3 = SapCommerceSourceView.from_dict(data)



            return response_201_type_3

        response_201 = _parse_response_201(response.json())

        return response_201

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ManualSourceInput | SapCommerceSourceInput | ShopifySourceInput | SitemapSourceInput,

) -> Response[ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]:
    """ Create a source

     Create a store configuration. Its stable string key is derived from its name; prices and
    runs use that key, while source-management paths use its UUID. GET /api/source-kinds
    describes accepted kinds and settings.

    Args:
        body (ManualSourceInput | SapCommerceSourceInput | ShopifySourceInput |
            SitemapSourceInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]
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
    body: ManualSourceInput | SapCommerceSourceInput | ShopifySourceInput | SitemapSourceInput,

) -> ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView | None:
    """ Create a source

     Create a store configuration. Its stable string key is derived from its name; prices and
    runs use that key, while source-management paths use its UUID. GET /api/source-kinds
    describes accepted kinds and settings.

    Args:
        body (ManualSourceInput | SapCommerceSourceInput | ShopifySourceInput |
            SitemapSourceInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ManualSourceInput | SapCommerceSourceInput | ShopifySourceInput | SitemapSourceInput,

) -> Response[ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]:
    """ Create a source

     Create a store configuration. Its stable string key is derived from its name; prices and
    runs use that key, while source-management paths use its UUID. GET /api/source-kinds
    describes accepted kinds and settings.

    Args:
        body (ManualSourceInput | SapCommerceSourceInput | ShopifySourceInput |
            SitemapSourceInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]
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
    body: ManualSourceInput | SapCommerceSourceInput | ShopifySourceInput | SitemapSourceInput,

) -> ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView | None:
    """ Create a source

     Create a store configuration. Its stable string key is derived from its name; prices and
    runs use that key, while source-management paths use its UUID. GET /api/source-kinds
    describes accepted kinds and settings.

    Args:
        body (ManualSourceInput | SapCommerceSourceInput | ShopifySourceInput |
            SitemapSourceInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
