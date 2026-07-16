from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from warden import __version__


class Metrics:
    def __init__(self, registry: CollectorRegistry) -> None:
        self.registry = registry
        self.searches_issued = Counter(
            "warden_searches_issued_total", "Searches issued by source", ["source"], registry=registry)
        self.paused_ticks = Counter(
            "warden_paused_ticks_total", "Ticks a source was quota-paused (× poll interval ≈ paused time)",
            ["source"], registry=registry)
        self.quota_remaining = Gauge(
            "warden_quota_remaining", "Remaining daily search budget", ["source"], registry=registry)
        self.daily_budget = Gauge(
            "warden_daily_budget", "Daily search budget after reserve", ["source"], registry=registry)
        self.binding_query_limit = Gauge(
            "warden_binding_query_limit", "Pre-reserve binding indexer query limit driving the budget",
            ["source"], registry=registry)
        self.quota_prowlarr = Gauge(
            "warden_quota_prowlarr", "1 if the budget came from Prowlarr indexer limits, 0 if the flat fallback",
            ["source"], registry=registry)
        self.indexers_total = Gauge(
            "warden_indexers_total", "Prowlarr indexers synced to this source", ["source"], registry=registry)
        self.indexers_defaulted = Gauge(
            "warden_indexers_defaulted", "Synced indexers with no Prowlarr limit (default cap applied)",
            ["source"], registry=registry)
        self.blocked = Gauge(
            "warden_blocked", "1 when a source is quota-paused", ["source"], registry=registry)
        self.space_blocked = Gauge(
            "warden_space_blocked", "1 when a source is space-paused (low disk headroom)",
            ["source"], registry=registry)
        self.space_paused_ticks = Counter(
            "warden_space_paused_ticks_total",
            "Ticks a source was space-paused (× poll interval ≈ paused time)",
            ["source"], registry=registry)
        self.free_bytes = Gauge(
            "warden_free_bytes", "Smallest free space across the source's *arr root folders",
            ["source"], registry=registry)
        self.projected_free_bytes = Gauge(
            "warden_projected_free_bytes", "Free bytes minus in-flight queue size_left (hunt headroom)",
            ["source"], registry=registry)
        self.instance_up = Gauge(
            "warden_instance_up", "1 when the *arr source responded this tick", ["source"], registry=registry)
        self.prowlarr_up = Gauge(
            "warden_prowlarr_up", "1 when the quota source (Prowlarr) responded this tick", registry=registry)
        self.last_tick = Gauge(
            "warden_last_tick_timestamp_seconds", "Unix time of the last completed tick", registry=registry)
        self.tick_duration = Histogram(
            "warden_tick_duration_seconds", "Tick duration", registry=registry)
        self.never_searched = Gauge(
            "warden_never_searched", "Missing items never searched (lastSearchTime null) — backlog not yet reached",
            ["source"], registry=registry)
        self.queue_size = Gauge(
            "warden_queue_size", "Items in the *arr download queue", ["source"], registry=registry)
        self.queue_stalled = Gauge(
            "warden_queue_stalled", "Removable-stale items detected this tick", ["source"], registry=registry)
        self.queue_no_progress = Gauge(
            "warden_queue_no_progress", "Downloads making no progress this tick (stuck)",
            ["source"], registry=registry)
        self.stale_removed = Counter(
            "warden_stale_removed_total", "Stale queue items removed + blocklisted",
            ["source", "reason"], registry=registry)
        self.stale_sweep_skipped = Counter(
            "warden_stale_sweep_skipped_total", "Ticks the sweep bailed (mass-unhealthy queue)",
            ["source"], registry=registry)
        self.search_hit = Counter(
            "warden_search_hit_total", "Searches that produced a grab, by source and indexer",
            ["source", "indexer"], registry=registry)
        self.search_miss = Counter(
            "warden_search_miss_total", "Searches that found nothing within the resolve window",
            ["source"], registry=registry)
        self.search_pending = Gauge(
            "warden_search_pending", "Searches awaiting reconciliation against grabs",
            ["source"], registry=registry)
        self.backoff_active = Gauge(
            "warden_backoff_active", "Items in cooldown (excluded from hunting as unfindable)",
            ["source"], registry=registry)
        self.backoff_entered = Counter(
            "warden_backoff_entered_total", "Items placed into backoff cooldown",
            ["source"], registry=registry)
        self.build_info = Gauge(
            "warden_build_info", "Warden build info (constant 1)", ["version"], registry=registry)
        self.build_info.labels(version=__version__).set(1)
