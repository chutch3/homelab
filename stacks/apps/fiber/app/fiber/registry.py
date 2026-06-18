from __future__ import annotations

from fiber.labels import parse_job
from fiber.models import DumpJob, MisconfiguredJob


def reconcile(
    services: dict[str, dict[str, str]],
) -> tuple[list[DumpJob], list[MisconfiguredJob], list[tuple[str, str]]]:
    jobs: list[DumpJob] = []
    misconfigured: list[MisconfiguredJob] = []
    skipped: list[tuple[str, str]] = []
    for service, labels in services.items():
        parsed = parse_job(service, labels)
        if isinstance(parsed, DumpJob):
            jobs.append(parsed)
        elif isinstance(parsed, MisconfiguredJob):
            misconfigured.append(parsed)
        else:
            # parse_job returned None — service has no fiber.enable label
            skipped.append((service, "no fiber.enable label"))
    return jobs, misconfigured, skipped
