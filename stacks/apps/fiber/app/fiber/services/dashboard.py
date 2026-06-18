from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime

from fiber.clients.bowl import BowlStorage
from fiber.models import DumpJob, MisconfiguredJob, MovementOutcome
from fiber.repositories.history import HistoryRepository
from fiber.services.registry_state import RegistryState
from fiber.services.worker_pool import WorkerPool
from fiber.status import DBStatus, derive_status, next_fire
from fiber.view import CardVM, Counts, DashboardVM, DiscoveryRow, DrawerVM

_ST_PLAIN = {
    "clean": "Backed up on schedule",
    "straining": "Dump in progress",
    "pinched": "Cancelled",
    "constipated": "Overdue — missed its window",
    "clogged": "Last dump failed",
    "misconfigured": "Bad labels — not backed up",
}


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n //= 1024
    return f"{n:.0f} PB"


def _fmt_elapsed(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def _build_labels(job: DumpJob) -> str:
    lines = [
        'deploy:',
        '  labels:',
        '    - "fiber.enable=true"',
        f'    - "fiber.engine={job.engine.value}"',
        f'    - "fiber.dbname={job.dbname}"',
        f'    - "fiber.user={job.user}"',
        f'    - "fiber.secret={job.secret}"',
        f'    - "fiber.schedule={job.schedule}"',
    ]
    if job.path:
        lines.append(f'    - "fiber.path={job.path}"')
    if job.app:
        lines.append(f'    - "fiber.app={job.app}"')
    return "\n".join(lines)


class DashboardService:
    def __init__(
        self,
        registry_state: RegistryState,
        history: HistoryRepository,
        pool: WorkerPool,
        bowl: BowlStorage,
        now: Callable[[], datetime],
        default_bowl_root: str,
    ) -> None:
        self._registry_state = registry_state
        self._history = history
        self._pool = pool
        self._bowl = bowl
        self._now = now
        self._default_bowl_root = default_bowl_root

    def build(self) -> DashboardVM:
        snap = self._registry_state.get()
        now = self._now()
        cards: list[CardVM] = []

        for job in snap.jobs:
            running_since = self._pool.started_at(job.service)
            last_success = self._history.last_success(job.service)
            last_outcome: MovementOutcome | None = self._history.last_outcome(job.service)
            latest_clean = self._history.latest_clean(job.service)
            status = derive_status(
                misconfigured=False,
                running=running_since is not None,
                last_outcome=last_outcome,
                last_success=last_success,
                schedule=job.schedule,
                now=now,
            )
            progress: str | None = None
            if running_since is not None:
                entries = self._bowl.list_entries(job.service)
                temp_bytes = next(
                    (e.size_bytes for e in entries if e.is_temp), 0
                )
                elapsed_s = int((now - running_since).total_seconds())
                progress = f"{_fmt_bytes(temp_bytes)} · {_fmt_elapsed(elapsed_s)}"
                next_run_str = "in progress"
            else:
                next_run_str = _rel_future(next_fire(job.schedule, now), now)
            cards.append(CardVM(
                service=job.service,
                engine=job.engine.value,
                status=status,
                last_rel=_rel_time(last_success, now) if last_success else "never",
                size=_fmt_bytes(latest_clean.bytes_written) if latest_clean else "—",
                next_run=next_run_str,
                bristol=latest_clean.bristol_type if latest_clean else None,
                writes_to=job.path or self._default_bowl_root,
                error=None,
                progress=progress,
            ))

        for m in snap.misconfigured:
            cards.append(CardVM(
                service=m.service,
                engine="—",
                status=DBStatus.MISCONFIGURED,
                last_rel="never",
                size="—",
                next_run="—",
                bristol=None,
                writes_to=self._default_bowl_root,
                error=", ".join(m.errors),
            ))

        cards.sort(key=lambda c: (-c.severity, c.service))

        discovery: list[DiscoveryRow] = []
        for job in snap.jobs:
            discovery.append(DiscoveryRow(service=job.service, result="discovered", detail=job.engine.value))
        for m in snap.misconfigured:
            discovery.append(DiscoveryRow(service=m.service, result="misconfigured", detail=", ".join(m.errors)))
        for svc, reason in snap.skipped:
            discovery.append(DiscoveryRow(service=svc, result="skipped", detail=reason))

        used_bytes, free_bytes = self._bowl.usage()

        discovery_rel = _rel_time(snap.scanned_at, now) if snap.scanned_at else "—"

        return DashboardVM(
            cards=cards,
            counts=Counts.from_cards(cards),
            discovery=discovery,
            bowl_path=self._default_bowl_root,
            bowl_used=_fmt_bytes(used_bytes),
            bowl_free=_fmt_bytes(free_bytes),
            discovery_rel=discovery_rel,
            discovery_error=snap.error,
        )


    def card(self, service: str) -> CardVM:
        """Return a single card VM for the given service (used for SSE/HTMX tile re-renders)."""
        vm = self.build()
        for c in vm.cards:
            if c.service == service:
                return c
        # If not found (e.g. service was removed), return a minimal card
        return CardVM(
            service=service,
            engine="—",
            status=DBStatus.MISCONFIGURED,
            last_rel="—",
            size="—",
            next_run="—",
            bristol=None,
            writes_to=self._default_bowl_root,
            error="not found",
        )

    def detail(self, service: str) -> DrawerVM:
        """Return the rich drawer VM for a service."""
        snap = self._registry_state.get()
        now = self._now()

        # --- find the job or misconfigured entry ---
        job: DumpJob | None = next((j for j in snap.jobs if j.service == service), None)
        misc: MisconfiguredJob | None = next(
            (m for m in snap.misconfigured if m.service == service), None
        )

        if misc is not None:
            return DrawerVM(
                service=service,
                engine="—",
                status=DBStatus.MISCONFIGURED,
                plain="Bad labels — not backed up",
                last_rel="never",
                size="—",
                next_run="—",
                writes_to=self._default_bowl_root,
                bristol=None,
                app_version=None,
                sha=None,
                fmt="—",
                timeline=[],
                sample=None,
                labels="",
                error=", ".join(misc.errors),
            )

        if job is None:
            return DrawerVM(
                service=service,
                engine="—",
                status=DBStatus.MISCONFIGURED,
                plain="Bad labels — not backed up",
                last_rel="—",
                size="—",
                next_run="—",
                writes_to=self._default_bowl_root,
                bristol=None,
                app_version=None,
                sha=None,
                fmt="—",
                timeline=[],
                sample=None,
                labels="",
                error="not found",
            )

        # --- build timeline ---
        recent = self._history.recent(service, 5)
        timeline: list[tuple[str, str]] = [
            (_rel_time(r.finished_at, now), r.outcome.value) for r in recent
        ]

        # --- latest clean movement ---
        clean_rows = [r for r in recent if r.outcome is MovementOutcome.CLEAN]
        latest_clean = clean_rows[0] if clean_rows else None

        bristol = latest_clean.bristol_type if latest_clean else None
        size = _fmt_bytes(latest_clean.bytes_written) if latest_clean else "—"
        app_version = latest_clean.app_image if latest_clean else None

        # sha from receipt JSON
        sha: str | None = None
        if latest_clean and latest_clean.receipt_path:
            raw = self._bowl.read_text(latest_clean.receipt_path)
            if raw:
                try:
                    sha = json.loads(raw).get("sha256")
                except (json.JSONDecodeError, AttributeError):
                    sha = None

        # stool sample from latest clogged movement
        clogged_rows = [r for r in recent if r.outcome is MovementOutcome.CLOGGED]
        latest_clogged = clogged_rows[0] if clogged_rows else None
        sample: str | None = None
        if latest_clogged and latest_clogged.sample_path:
            sample = self._bowl.read_text(latest_clogged.sample_path)

        running_since = self._pool.started_at(service)
        last_success = self._history.last_success(service)
        last_outcome = self._history.last_outcome(service)
        status = derive_status(
            misconfigured=False,
            running=running_since is not None,
            last_outcome=last_outcome,
            last_success=last_success,
            schedule=job.schedule,
            now=now,
        )

        detail_next_run = (
            "in progress"
            if running_since is not None
            else _rel_future(next_fire(job.schedule, now), now)
        )
        return DrawerVM(
            service=service,
            engine=job.engine.value,
            status=status,
            plain=_ST_PLAIN.get(status.value, status.value),
            last_rel=_rel_time(last_success, now) if last_success else "never",
            size=size,
            next_run=detail_next_run,
            writes_to=job.path or self._default_bowl_root,
            bristol=bristol,
            app_version=app_version,
            sha=sha,
            fmt=job.fmt.value,
            timeline=timeline,
            sample=sample,
            labels=_build_labels(job),
            error=None,
        )


def _rel_future(dt: datetime, now: datetime) -> str:
    delta = dt - now
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"in {seconds}s"
    if seconds < 3600:
        return f"in {seconds // 60}m"
    if seconds < 86400:
        return f"in {seconds // 3600}h"
    return f"in {seconds // 86400}d"


def _rel_time(dt: datetime, now: datetime) -> str:
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"
