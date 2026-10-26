from typing import Literal

SitemapSourceViewTransport = Literal['browser', 'direct']

SITEMAP_SOURCE_VIEW_TRANSPORT_VALUES: set[SitemapSourceViewTransport] = { 'browser', 'direct',  }

def check_sitemap_source_view_transport(value: str) -> SitemapSourceViewTransport:
    if value in SITEMAP_SOURCE_VIEW_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SITEMAP_SOURCE_VIEW_TRANSPORT_VALUES!r}")
