from fiber.registry import reconcile
from fiber.models import DumpJob, MisconfiguredJob


def test_splits_valid_and_misconfigured_and_skips_unenrolled() -> None:
    services = {
        "kenku-pg": {"fiber.enable": "true", "fiber.dbname": "k", "fiber.user": "k", "fiber.secret": "s"},
        "broken-pg": {"fiber.enable": "true"},
        "plain-pg": {},
    }
    jobs, misconfigured, skipped = reconcile(services)
    assert [j.service for j in jobs] == ["kenku-pg"]
    assert all(isinstance(j, DumpJob) for j in jobs)
    assert [m.service for m in misconfigured] == ["broken-pg"]
    assert all(isinstance(m, MisconfiguredJob) for m in misconfigured)


def test_reconcile_returns_skipped_services_without_fiber_enable() -> None:
    services = {
        "traefik": {},
        "immich": {"some.label": "true"},
    }
    jobs, misconfigured, skipped = reconcile(services)
    assert jobs == []
    assert misconfigured == []
    assert len(skipped) == 2
    skipped_services = [s for s, _ in skipped]
    assert "traefik" in skipped_services
    assert "immich" in skipped_services
    for svc, reason in skipped:
        assert reason == "no fiber.enable label"
