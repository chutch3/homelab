from typing import Literal

SitemapSourceViewBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SITEMAP_SOURCE_VIEW_BASIS_VALUES: set[SitemapSourceViewBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_sitemap_source_view_basis(value: str) -> SitemapSourceViewBasis:
    if value in SITEMAP_SOURCE_VIEW_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SITEMAP_SOURCE_VIEW_BASIS_VALUES!r}")
