from __future__ import annotations

from croniter import croniter

from fiber.models import DumpFormat, DumpJob, Engine, MisconfiguredJob

_DEFAULTS = {"schedule": "0 3 * * *", "retain": 7, "format": "custom", "jobs": 1, "port_pg": 5432, "port_mysql": 3306}


def _duration_seconds(raw: str) -> float:
    raw = raw.strip()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if raw[-1] in units:
        return float(raw[:-1]) * units[raw[-1]]
    return float(raw)


def parse_job(service: str, labels: dict[str, str], active_provider: str = "swarm") -> DumpJob | MisconfiguredJob | None:
    if labels.get("fiber.enable", "").lower() != "true":
        return None

    effective_provider = labels.get("fiber.provider", "swarm")
    if effective_provider != active_provider:
        return MisconfiguredJob(
            service=service,
            errors=(f"provider mismatch: label={effective_provider}, active={active_provider}",),
        )

    errors: list[str] = []
    for key in ("dbname", "user", "secret"):
        if not labels.get(f"fiber.{key}"):
            errors.append(f"missing fiber.{key}")
    if errors:
        return MisconfiguredJob(service=service, errors=tuple(errors))

    schedule = labels.get("fiber.schedule", _DEFAULTS["schedule"])
    if not croniter.is_valid(schedule):
        return MisconfiguredJob(service=service, errors=(f"invalid cron: '{schedule}'",))

    engine = Engine(labels.get("fiber.engine", "postgres"))
    default_port = _DEFAULTS["port_pg"] if engine is Engine.POSTGRES else _DEFAULTS["port_mysql"]
    options = tuple(labels.get("fiber.options", "").split())
    timeout_raw = labels.get("fiber.timeout")

    return DumpJob(
        service=service,
        engine=engine,
        host=labels.get("fiber.host", service),
        port=int(labels.get("fiber.port", default_port)),
        dbname=labels["fiber.dbname"],
        user=labels["fiber.user"],
        secret=labels["fiber.secret"],
        schedule=labels.get("fiber.schedule", _DEFAULTS["schedule"]),
        options=options,
        retain=int(labels.get("fiber.retain", _DEFAULTS["retain"])),
        fmt=DumpFormat(labels.get("fiber.format", _DEFAULTS["format"])),
        jobs=int(labels.get("fiber.jobs", _DEFAULTS["jobs"])),
        timeout=_duration_seconds(timeout_raw) if timeout_raw else None,
        app=labels.get("fiber.app"),
        schema_version_query=labels.get("fiber.schema_version_query"),
        path=labels.get("fiber.path"),
    )
