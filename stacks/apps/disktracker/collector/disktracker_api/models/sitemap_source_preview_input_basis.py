from typing import Literal

SitemapSourcePreviewInputBasis = Literal['open_api', 'permission', 'terms_allow', 'unconfirmed']

SITEMAP_SOURCE_PREVIEW_INPUT_BASIS_VALUES: set[SitemapSourcePreviewInputBasis] = { 'open_api', 'permission', 'terms_allow', 'unconfirmed',  }

def check_sitemap_source_preview_input_basis(value: str) -> SitemapSourcePreviewInputBasis:
    if value in SITEMAP_SOURCE_PREVIEW_INPUT_BASIS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {SITEMAP_SOURCE_PREVIEW_INPUT_BASIS_VALUES!r}")
