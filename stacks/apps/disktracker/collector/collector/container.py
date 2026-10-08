"""The composition root: every object the collector runs with is created here, once, by a
provider, and handed to whatever depends on it. Nothing is constructed later: what changes from
one source to the next (its store, settings and transport) is passed to these objects when they
are called."""

import os
from collections.abc import Iterator

import httpx
from dependency_injector import containers, providers

from collector.api import serve
from collector.browser import MAX_TIMEOUT_MS, BrowserHttp
from collector.clients.disktracker import DisktrackerClient
from collector.clock import SystemClock
from collector.collection import Collector
from collector.config import Config
from collector.inspect import Inspector
from collector.pacer import Pacer
from collector.polite import PoliteHttp
from collector.preview import Previewer
from collector.schedule import Schedule
from collector.sites import Sites
from collector.sources.sap_commerce import SapCommerce
from collector.sources.shopify import Shopify
from collector.sources.sitemap import Sitemap
from disktracker_api import Client


def store_http(proxy_url: str | None) -> Iterator[httpx.Client]:
    """What stores are fetched with: through the proxy when there is one, and never around it,
    so a proxy that is down fails a fetch rather than showing the store the collector."""
    # ServerPartDeals redirects product pages between www. and the bare domain.
    with httpx.Client(timeout=30.0, follow_redirects=True, proxy=proxy_url) as http:
        yield http


def flaresolverr_http() -> Iterator[httpx.Client]:
    # FlareSolverr answers once the browser has the page, or has given up on it.
    with httpx.Client(timeout=MAX_TIMEOUT_MS / 1000 + 30) as http:
        yield http


def disktracker_api(base_url: str) -> Iterator[Client]:
    with Client(base_url=base_url, timeout=httpx.Timeout(30.0)) as api:
        yield api


class Container(containers.DeclarativeContainer):
    config = providers.Singleton(Config.from_env, environ=providers.Object(os.environ))
    clock = providers.Singleton(SystemClock)
    store_client = providers.Resource(store_http, proxy_url=config.provided.proxy_url)
    flaresolverr_client = providers.Resource(flaresolverr_http)
    api = providers.Resource(disktracker_api, base_url=config.provided.disktracker_url)
    browser = providers.Singleton(
        BrowserHttp,
        http=flaresolverr_client,
        flaresolverr_url=config.provided.flaresolverr_url,
        proxy_url=config.provided.proxy_url,
    )
    # The reader for each kind of source: made once, and given each site it is to read.
    readers = providers.Dict(
        shopify=providers.Singleton(Shopify),
        sitemap=providers.Singleton(Sitemap),
        sap_commerce=providers.Singleton(SapCommerce),
    )
    disktracker = providers.Singleton(
        DisktrackerClient, api=api, retry_delay=config.provided.retry_delay_seconds, clock=clock
    )

    # Scheduled runs. One pacer, so a store's requests are spaced however they are fetched.
    pacer = providers.Singleton(Pacer, clock=clock)
    polite = providers.Singleton(PoliteHttp, http=store_client, pacer=pacer, clock=clock)
    browser_polite = providers.Singleton(PoliteHttp, http=browser, pacer=pacer, clock=clock)
    sites = providers.Singleton(
        Sites,
        readers=readers,
        transports=providers.Dict(direct=polite, browser=browser_polite),
        min_delay=config.provided.min_delay_seconds,
    )
    collector = providers.Singleton(Collector, disktracker=disktracker, sites=sites, clock=clock)
    schedule = providers.Singleton(
        Schedule,
        disktracker=disktracker,
        collector=collector,
        run_once=config.provided.run_once,
        poll_seconds=config.provided.poll_seconds,
    )

    # Previews. Their own pacer, so a preview never waits behind a scheduled run; it waits only
    # as long as the store itself asks between its own few requests.
    preview_pacer = providers.Singleton(Pacer, clock=clock)
    preview_polite = providers.Singleton(
        PoliteHttp, http=store_client, pacer=preview_pacer, clock=clock
    )
    preview_browser_polite = providers.Singleton(
        PoliteHttp, http=browser, pacer=preview_pacer, clock=clock
    )
    preview_sites = providers.Singleton(
        Sites,
        readers=readers,
        transports=providers.Dict(direct=preview_polite, browser=preview_browser_polite),
        min_delay=0,
    )
    previewer = providers.Singleton(
        Previewer, sites=preview_sites, clock=clock, time_limit=config.provided.preview_seconds
    )
    inspector = providers.Singleton(
        Inspector,
        sites=preview_sites,
        clock=clock,
        time_limit=config.provided.preview_seconds,
        run_delay=config.provided.min_delay_seconds,
    )
    preview_api = providers.Resource(
        serve, previewer=previewer, inspector=inspector, port=config.provided.api_port
    )
