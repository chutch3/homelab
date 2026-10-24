from typing import Literal

SitemapSourceInputTransport = Literal['browser', 'direct']

SITEMAP_SOURCE_INPUT_TRANSPORT_VALUES: set[SitemapSourceInputTransport] = { 'browser', 'direct',  }

def check_sitemap_source_input_transport(value: str) -> SitemapSourceInputTransport:
    if value in SITEMAP_SOURCE_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SITEMAP_SOURCE_INPUT_TRANSPORT_VALUES!r}")
