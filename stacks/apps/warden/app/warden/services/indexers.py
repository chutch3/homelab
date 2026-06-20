from __future__ import annotations

from warden.models import Indexer, ProwlarrApp


def serves_app(indexer: Indexer, app: ProwlarrApp) -> bool:
    """Replicates Prowlarr's sync rule: enabled, tag-match (or app has no tags),
    and at least one indexer category in the app's sync categories."""
    if not indexer.enabled:
        return False
    tag_ok = (not app.tags) or bool(set(indexer.tags) & set(app.tags))
    cat_ok = bool(set(indexer.categories) & set(app.sync_categories))
    return tag_ok and cat_ok


def indexers_for_app(app: ProwlarrApp, indexers: list[Indexer]) -> list[Indexer]:
    return [i for i in indexers if serves_app(i, app)]


def effective_cap(indexer: Indexer, default_cap: int) -> int:
    """An indexer's per-day query ceiling — its Prowlarr limit, or the default
    when Prowlarr tracks no limit (no indexer is truly unlimited)."""
    return indexer.query_limit if indexer.query_limit is not None else default_cap


def source_gross_limit(indexers: list[Indexer], default_cap: int) -> int:
    """A source's daily query budget = the smallest effective cap among its
    indexers (a hunt queries them all at once, so the source can't out-search its
    most-constrained indexer without burning it). Zero when no indexers serve it."""
    if not indexers:
        return 0
    return min(effective_cap(i, default_cap) for i in indexers)
