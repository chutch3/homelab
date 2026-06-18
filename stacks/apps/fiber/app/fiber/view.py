from __future__ import annotations

from dataclasses import dataclass, field

from fiber.status import DBStatus

_SEVERITY = {
    DBStatus.CLOGGED: 3,
    DBStatus.MISCONFIGURED: 3,
    DBStatus.CONSTIPATED: 2,
    DBStatus.STRAINING: 1,
    DBStatus.PINCHED: 1,
    DBStatus.CLEAN: 0,
}


@dataclass(frozen=True)
class CardVM:
    service: str
    engine: str
    status: DBStatus
    last_rel: str
    size: str
    next_run: str
    bristol: int | None
    writes_to: str
    error: str | None
    progress: str | None = None

    @property
    def severity(self) -> int:
        return _SEVERITY[self.status]


@dataclass(frozen=True)
class DiscoveryRow:
    service: str
    result: str  # "discovered" | "misconfigured" | "skipped"
    detail: str


@dataclass(frozen=True)
class Counts:
    by_status: dict[DBStatus, int] = field(default_factory=dict)

    @staticmethod
    def from_cards(cards: list[CardVM]) -> Counts:
        d: dict[DBStatus, int] = {}
        for c in cards:
            d[c.status] = d.get(c.status, 0) + 1
        return Counts(by_status=d)


@dataclass(frozen=True)
class DashboardVM:
    cards: list[CardVM]
    counts: Counts
    discovery: list[DiscoveryRow]
    bowl_path: str
    bowl_used: str
    bowl_free: str
    discovery_rel: str = "—"
    discovery_error: str | None = None

    @property
    def needs_attention(self) -> int:
        return sum(1 for c in self.cards if c.severity >= 2)

    @property
    def verdict_ok(self) -> bool:
        return self.needs_attention == 0


@dataclass(frozen=True)
class DrawerVM:
    service: str
    engine: str
    status: DBStatus
    plain: str
    last_rel: str
    size: str
    next_run: str
    writes_to: str
    bristol: int | None
    app_version: str | None
    sha: str | None
    fmt: str
    timeline: list[tuple[str, str]]  # (rel_label, outcome_value)
    sample: str | None
    labels: str
    error: str | None
