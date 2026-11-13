from typing import Literal

SitemapSourceInputBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SITEMAP_SOURCE_INPUT_BASIS_VALUES: set[SitemapSourceInputBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_sitemap_source_input_basis(value: str) -> SitemapSourceInputBasis:
    if value in SITEMAP_SOURCE_INPUT_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SITEMAP_SOURCE_INPUT_BASIS_VALUES!r}")
