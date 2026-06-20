from warden.services.indexers import (effective_cap, indexers_for_app,
                                       serves_app, source_gross_limit)
from tests.factories import indexer, prowlarr_app

RADARR = prowlarr_app(implementation="Radarr", tags=(2, 1), sync_categories=(2000, 2040))


def test_serves_when_tag_and_category_match():
    assert serves_app(indexer(tags=(1,), categories=(2000,)), RADARR) is True


def test_not_served_when_disabled():
    assert serves_app(indexer(enabled=False), RADARR) is False


def test_not_served_when_no_tag_overlap():
    assert serves_app(indexer(tags=(9,), categories=(2000,)), RADARR) is False


def test_not_served_when_no_category_overlap():
    assert serves_app(indexer(tags=(1,), categories=(5000,)), RADARR) is False


def test_indexers_for_app_filters_to_matching_enabled():
    items = [indexer(id=1, categories=(2000,)), indexer(id=2, categories=(5000,)),
             indexer(id=3, enabled=False)]
    assert [i.id for i in indexers_for_app(RADARR, items)] == [1]


def test_effective_cap_uses_query_limit_when_set():
    assert effective_cap(indexer(query_limit=20), default_cap=100) == 20


def test_effective_cap_uses_default_when_none():
    assert effective_cap(indexer(query_limit=None), default_cap=100) == 100


def test_source_gross_limit_is_min_effective_cap():
    # a hunt queries every indexer, so the budget is bound by the most-constrained one
    items = [indexer(id=1, query_limit=20), indexer(id=2, query_limit=None)]
    assert source_gross_limit(items, default_cap=100) == 20


def test_source_gross_limit_zero_when_no_indexers():
    assert source_gross_limit([], default_cap=100) == 0
