from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.market import Market
from ...models.market_condition_item import check_market_condition_item
from ...models.market_condition_item import MarketConditionItem
from ...models.market_form_factor_type_0 import check_market_form_factor_type_0
from ...models.market_form_factor_type_0 import MarketFormFactorType0
from ...models.market_intended_use_type_0 import check_market_intended_use_type_0
from ...models.market_intended_use_type_0 import MarketIntendedUseType0
from ...models.market_interface_type_0 import check_market_interface_type_0
from ...models.market_interface_type_0 import MarketInterfaceType0
from ...models.market_media_type_type_0 import check_market_media_type_type_0
from ...models.market_media_type_type_0 import MarketMediaTypeType0
from ...models.market_range_days import check_market_range_days
from ...models.market_range_days import MarketRangeDays
from ...models.market_recording_type_type_0 import check_market_recording_type_type_0
from ...models.market_recording_type_type_0 import MarketRecordingTypeType0
from ...models.market_sort import check_market_sort
from ...models.market_sort import MarketSort
from ...types import UNSET, Unset
from typing import cast
from typing import Literal, cast
from uuid import UUID



def _get_kwargs(
    *,
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[MarketConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: MarketMediaTypeType0 | None | Unset = UNSET,
    form_factor: MarketFormFactorType0 | None | Unset = UNSET,
    interface: MarketInterfaceType0 | None | Unset = UNSET,
    recording_type: MarketRecordingTypeType0 | None | Unset = UNSET,
    intended_use: Literal['unknown'] | MarketIntendedUseType0 | None | Unset = UNSET,
    recent_days: int | Unset = 7,
    range_days: MarketRangeDays | Unset = 90,
    drive_id: None | Unset | UUID = UNSET,
    max_total_cents: int | None | Unset = UNSET,
    in_stock: bool | Unset = True,
    recent_only: bool | Unset = False,
    sort: MarketSort | Unset = 'unit-asc',
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    params["q"] = q

    json_brand: list[str] | Unset = UNSET
    if not isinstance(brand, Unset):
        json_brand = brand


    params["brand"] = json_brand

    json_capacity: list[int] | Unset = UNSET
    if not isinstance(capacity, Unset):
        json_capacity = capacity


    params["capacity"] = json_capacity

    json_condition: list[str] | Unset = UNSET
    if not isinstance(condition, Unset):
        json_condition = []
        for condition_item_data in condition:
            condition_item: str = condition_item_data
            json_condition.append(condition_item)


    params["condition"] = json_condition

    json_store: list[str] | Unset = UNSET
    if not isinstance(store, Unset):
        json_store = store


    params["store"] = json_store

    json_media_type: None | str | Unset
    if isinstance(media_type, Unset):
        json_media_type = UNSET
    elif isinstance(media_type, str):
        json_media_type = media_type
    else:
        json_media_type = media_type
    params["media_type"] = json_media_type

    json_form_factor: None | str | Unset
    if isinstance(form_factor, Unset):
        json_form_factor = UNSET
    elif isinstance(form_factor, str):
        json_form_factor = form_factor
    else:
        json_form_factor = form_factor
    params["form_factor"] = json_form_factor

    json_interface: None | str | Unset
    if isinstance(interface, Unset):
        json_interface = UNSET
    elif isinstance(interface, str):
        json_interface = interface
    else:
        json_interface = interface
    params["interface"] = json_interface

    json_recording_type: None | str | Unset
    if isinstance(recording_type, Unset):
        json_recording_type = UNSET
    elif isinstance(recording_type, str):
        json_recording_type = recording_type
    else:
        json_recording_type = recording_type
    params["recording_type"] = json_recording_type

    json_intended_use: Literal['unknown'] | None | str | Unset
    if isinstance(intended_use, Unset):
        json_intended_use = UNSET
    elif isinstance(intended_use, str):
        json_intended_use = intended_use
    else:
        json_intended_use = intended_use
    params["intended_use"] = json_intended_use

    params["recent_days"] = recent_days

    json_range_days: int | Unset = UNSET
    if not isinstance(range_days, Unset):
        json_range_days = range_days

    params["range_days"] = json_range_days

    json_drive_id: None | str | Unset
    if isinstance(drive_id, Unset):
        json_drive_id = UNSET
    elif isinstance(drive_id, UUID):
        json_drive_id = str(drive_id)
    else:
        json_drive_id = drive_id
    params["drive_id"] = json_drive_id

    json_max_total_cents: int | None | Unset
    if isinstance(max_total_cents, Unset):
        json_max_total_cents = UNSET
    else:
        json_max_total_cents = max_total_cents
    params["max_total_cents"] = json_max_total_cents

    params["in_stock"] = in_stock

    params["recent_only"] = recent_only

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort

    params["sort"] = json_sort

    params["limit"] = limit

    params["offset"] = offset


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/reports/market",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | Market | None:
    if response.status_code == 200:
        response_200 = Market.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | Market]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[MarketConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: MarketMediaTypeType0 | None | Unset = UNSET,
    form_factor: MarketFormFactorType0 | None | Unset = UNSET,
    interface: MarketInterfaceType0 | None | Unset = UNSET,
    recording_type: MarketRecordingTypeType0 | None | Unset = UNSET,
    intended_use: Literal['unknown'] | MarketIntendedUseType0 | None | Unset = UNSET,
    recent_days: int | Unset = 7,
    range_days: MarketRangeDays | Unset = 90,
    drive_id: None | Unset | UUID = UNSET,
    max_total_cents: int | None | Unset = UNSET,
    in_stock: bool | Unset = True,
    recent_only: bool | Unset = False,
    sort: MarketSort | Unset = 'unit-asc',
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> Response[HTTPValidationError | Market]:
    """ Read the market for drives

     The drives that match, a page at a time, each shown by its cheapest matching offer in
    stock, with how many stores and sellers offer it and what each condition it is offered in
    costs among the matches, and the range of its price; with the lowest prices among every
    match, the filter options of every drive, and how many drives there are to buy at all.

    Repeat a parameter for several choices, e.g. `brand=Seagate&brand=Toshiba`. Choices within
    a filter use OR; different filters use AND. Filters match offers, then group them by drive.
    Each filter option counts the drives choosing it would give, with every other filter as
    asked. total counts matching drives before pagination; offers counts matching offers. Only
    offers that count (none held for review) are in the market. drive_id: whether one drive is
    among the matches.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[MarketConditionItem] | Unset): Condition choices; repeat the parameter for
            multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (MarketMediaTypeType0 | None | Unset):
        form_factor (MarketFormFactorType0 | None | Unset):
        interface (MarketInterfaceType0 | None | Unset):
        recording_type (MarketRecordingTypeType0 | None | Unset):
        intended_use (Literal['unknown'] | MarketIntendedUseType0 | None | Unset):
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (MarketRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.
        drive_id (None | Unset | UUID): Only this drive, if it matches
        max_total_cents (int | None | Unset): Maximum item price plus known shipping, in US cents.
        in_stock (bool | Unset): Only offers in stock; false for all Default: True.
        recent_only (bool | Unset): Only offers checked recently Default: False.
        sort (MarketSort | Unset): unit sorts by total dollars per TB; total includes known
            shipping; checked sorts by last check time. Default: 'unit-asc'.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Market]
     """


    kwargs = _get_kwargs(
        q=q,
brand=brand,
capacity=capacity,
condition=condition,
store=store,
media_type=media_type,
form_factor=form_factor,
interface=interface,
recording_type=recording_type,
intended_use=intended_use,
recent_days=recent_days,
range_days=range_days,
drive_id=drive_id,
max_total_cents=max_total_cents,
in_stock=in_stock,
recent_only=recent_only,
sort=sort,
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
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[MarketConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: MarketMediaTypeType0 | None | Unset = UNSET,
    form_factor: MarketFormFactorType0 | None | Unset = UNSET,
    interface: MarketInterfaceType0 | None | Unset = UNSET,
    recording_type: MarketRecordingTypeType0 | None | Unset = UNSET,
    intended_use: Literal['unknown'] | MarketIntendedUseType0 | None | Unset = UNSET,
    recent_days: int | Unset = 7,
    range_days: MarketRangeDays | Unset = 90,
    drive_id: None | Unset | UUID = UNSET,
    max_total_cents: int | None | Unset = UNSET,
    in_stock: bool | Unset = True,
    recent_only: bool | Unset = False,
    sort: MarketSort | Unset = 'unit-asc',
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> HTTPValidationError | Market | None:
    """ Read the market for drives

     The drives that match, a page at a time, each shown by its cheapest matching offer in
    stock, with how many stores and sellers offer it and what each condition it is offered in
    costs among the matches, and the range of its price; with the lowest prices among every
    match, the filter options of every drive, and how many drives there are to buy at all.

    Repeat a parameter for several choices, e.g. `brand=Seagate&brand=Toshiba`. Choices within
    a filter use OR; different filters use AND. Filters match offers, then group them by drive.
    Each filter option counts the drives choosing it would give, with every other filter as
    asked. total counts matching drives before pagination; offers counts matching offers. Only
    offers that count (none held for review) are in the market. drive_id: whether one drive is
    among the matches.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[MarketConditionItem] | Unset): Condition choices; repeat the parameter for
            multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (MarketMediaTypeType0 | None | Unset):
        form_factor (MarketFormFactorType0 | None | Unset):
        interface (MarketInterfaceType0 | None | Unset):
        recording_type (MarketRecordingTypeType0 | None | Unset):
        intended_use (Literal['unknown'] | MarketIntendedUseType0 | None | Unset):
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (MarketRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.
        drive_id (None | Unset | UUID): Only this drive, if it matches
        max_total_cents (int | None | Unset): Maximum item price plus known shipping, in US cents.
        in_stock (bool | Unset): Only offers in stock; false for all Default: True.
        recent_only (bool | Unset): Only offers checked recently Default: False.
        sort (MarketSort | Unset): unit sorts by total dollars per TB; total includes known
            shipping; checked sorts by last check time. Default: 'unit-asc'.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Market
     """


    return sync_detailed(
        client=client,
q=q,
brand=brand,
capacity=capacity,
condition=condition,
store=store,
media_type=media_type,
form_factor=form_factor,
interface=interface,
recording_type=recording_type,
intended_use=intended_use,
recent_days=recent_days,
range_days=range_days,
drive_id=drive_id,
max_total_cents=max_total_cents,
in_stock=in_stock,
recent_only=recent_only,
sort=sort,
limit=limit,
offset=offset,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[MarketConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: MarketMediaTypeType0 | None | Unset = UNSET,
    form_factor: MarketFormFactorType0 | None | Unset = UNSET,
    interface: MarketInterfaceType0 | None | Unset = UNSET,
    recording_type: MarketRecordingTypeType0 | None | Unset = UNSET,
    intended_use: Literal['unknown'] | MarketIntendedUseType0 | None | Unset = UNSET,
    recent_days: int | Unset = 7,
    range_days: MarketRangeDays | Unset = 90,
    drive_id: None | Unset | UUID = UNSET,
    max_total_cents: int | None | Unset = UNSET,
    in_stock: bool | Unset = True,
    recent_only: bool | Unset = False,
    sort: MarketSort | Unset = 'unit-asc',
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> Response[HTTPValidationError | Market]:
    """ Read the market for drives

     The drives that match, a page at a time, each shown by its cheapest matching offer in
    stock, with how many stores and sellers offer it and what each condition it is offered in
    costs among the matches, and the range of its price; with the lowest prices among every
    match, the filter options of every drive, and how many drives there are to buy at all.

    Repeat a parameter for several choices, e.g. `brand=Seagate&brand=Toshiba`. Choices within
    a filter use OR; different filters use AND. Filters match offers, then group them by drive.
    Each filter option counts the drives choosing it would give, with every other filter as
    asked. total counts matching drives before pagination; offers counts matching offers. Only
    offers that count (none held for review) are in the market. drive_id: whether one drive is
    among the matches.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[MarketConditionItem] | Unset): Condition choices; repeat the parameter for
            multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (MarketMediaTypeType0 | None | Unset):
        form_factor (MarketFormFactorType0 | None | Unset):
        interface (MarketInterfaceType0 | None | Unset):
        recording_type (MarketRecordingTypeType0 | None | Unset):
        intended_use (Literal['unknown'] | MarketIntendedUseType0 | None | Unset):
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (MarketRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.
        drive_id (None | Unset | UUID): Only this drive, if it matches
        max_total_cents (int | None | Unset): Maximum item price plus known shipping, in US cents.
        in_stock (bool | Unset): Only offers in stock; false for all Default: True.
        recent_only (bool | Unset): Only offers checked recently Default: False.
        sort (MarketSort | Unset): unit sorts by total dollars per TB; total includes known
            shipping; checked sorts by last check time. Default: 'unit-asc'.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Market]
     """


    kwargs = _get_kwargs(
        q=q,
brand=brand,
capacity=capacity,
condition=condition,
store=store,
media_type=media_type,
form_factor=form_factor,
interface=interface,
recording_type=recording_type,
intended_use=intended_use,
recent_days=recent_days,
range_days=range_days,
drive_id=drive_id,
max_total_cents=max_total_cents,
in_stock=in_stock,
recent_only=recent_only,
sort=sort,
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
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[MarketConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: MarketMediaTypeType0 | None | Unset = UNSET,
    form_factor: MarketFormFactorType0 | None | Unset = UNSET,
    interface: MarketInterfaceType0 | None | Unset = UNSET,
    recording_type: MarketRecordingTypeType0 | None | Unset = UNSET,
    intended_use: Literal['unknown'] | MarketIntendedUseType0 | None | Unset = UNSET,
    recent_days: int | Unset = 7,
    range_days: MarketRangeDays | Unset = 90,
    drive_id: None | Unset | UUID = UNSET,
    max_total_cents: int | None | Unset = UNSET,
    in_stock: bool | Unset = True,
    recent_only: bool | Unset = False,
    sort: MarketSort | Unset = 'unit-asc',
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> HTTPValidationError | Market | None:
    """ Read the market for drives

     The drives that match, a page at a time, each shown by its cheapest matching offer in
    stock, with how many stores and sellers offer it and what each condition it is offered in
    costs among the matches, and the range of its price; with the lowest prices among every
    match, the filter options of every drive, and how many drives there are to buy at all.

    Repeat a parameter for several choices, e.g. `brand=Seagate&brand=Toshiba`. Choices within
    a filter use OR; different filters use AND. Filters match offers, then group them by drive.
    Each filter option counts the drives choosing it would give, with every other filter as
    asked. total counts matching drives before pagination; offers counts matching offers. Only
    offers that count (none held for review) are in the market. drive_id: whether one drive is
    among the matches.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[MarketConditionItem] | Unset): Condition choices; repeat the parameter for
            multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (MarketMediaTypeType0 | None | Unset):
        form_factor (MarketFormFactorType0 | None | Unset):
        interface (MarketInterfaceType0 | None | Unset):
        recording_type (MarketRecordingTypeType0 | None | Unset):
        intended_use (Literal['unknown'] | MarketIntendedUseType0 | None | Unset):
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (MarketRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.
        drive_id (None | Unset | UUID): Only this drive, if it matches
        max_total_cents (int | None | Unset): Maximum item price plus known shipping, in US cents.
        in_stock (bool | Unset): Only offers in stock; false for all Default: True.
        recent_only (bool | Unset): Only offers checked recently Default: False.
        sort (MarketSort | Unset): unit sorts by total dollars per TB; total includes known
            shipping; checked sorts by last check time. Default: 'unit-asc'.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Market
     """


    return (await asyncio_detailed(
        client=client,
q=q,
brand=brand,
capacity=capacity,
condition=condition,
store=store,
media_type=media_type,
form_factor=form_factor,
interface=interface,
recording_type=recording_type,
intended_use=intended_use,
recent_days=recent_days,
range_days=range_days,
drive_id=drive_id,
max_total_cents=max_total_cents,
in_stock=in_stock,
recent_only=recent_only,
sort=sort,
limit=limit,
offset=offset,

    )).parsed
