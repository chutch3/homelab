from typing import Literal

SitemapSourcePreviewInputTransport = Literal['browser', 'direct']

SITEMAP_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES: set[SitemapSourcePreviewInputTransport] = { 'browser', 'direct',  }

def check_sitemap_source_preview_input_transport(value: str) -> SitemapSourcePreviewInputTransport:
    if value in SITEMAP_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SITEMAP_SOURCE_PREVIEW_INPUT_TRANSPORT_VALUES!r}")
