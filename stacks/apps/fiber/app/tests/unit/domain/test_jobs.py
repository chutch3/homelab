from fiber.domain.jobs import parse_job, reconcile
from fiber.domain.models import DumpFormat, DumpJob, Engine, MisconfiguredJob


# ---------------------------------------------------------------------------
# parse_job — one service's labels
# ---------------------------------------------------------------------------

def test_returns_none_when_not_opted_in() -> None:
    assert parse_job("kenku-pg", {}) is None
    assert parse_job("kenku-pg", {"fiber.enable": "false"}) is None


def test_parses_a_full_valid_job() -> None:
    labels = {
        "fiber.enable": "true",
        "fiber.engine": "postgres",
        "fiber.dbname": "kenku",
        "fiber.user": "kenku",
        "fiber.secret": "kenku_db_password",
        "fiber.schedule": "0 3 * * *",
        "fiber.options": "--clean --if-exists",
        "fiber.retain": "5",
        "fiber.format": "directory",
        "fiber.jobs": "4",
        "fiber.timeout": "2h",
        "fiber.app": "downloads_kenku",
    }
    job = parse_job("kenku-pg", labels)
    assert isinstance(job, DumpJob)
    assert job.engine is Engine.POSTGRES
    assert job.host == "kenku-pg"  # defaults to service name
    assert job.port == 5432
    assert job.options == ("--clean", "--if-exists")
    assert job.retain == 5
    assert job.fmt is DumpFormat.DIRECTORY
    assert job.jobs == 4
    assert job.timeout == 7200.0
    assert job.app == "downloads_kenku"


def test_missing_required_keys_is_misconfigured() -> None:
    result = parse_job("kenku-pg", {"fiber.enable": "true"})
    assert isinstance(result, MisconfiguredJob)
    assert set(result.errors) == {"missing fiber.dbname", "missing fiber.user", "missing fiber.secret"}


def test_fiber_path_label_sets_job_path() -> None:
    labels = {
        "fiber.enable": "true",
        "fiber.dbname": "kenku",
        "fiber.user": "kenku",
        "fiber.secret": "pw",
        "fiber.path": "/mnt/big/kenku",
    }
    job = parse_job("kenku-pg", labels)
    assert isinstance(job, DumpJob)
    assert job.path == "/mnt/big/kenku"


def test_absent_fiber_path_label_leaves_job_path_none() -> None:
    labels = {
        "fiber.enable": "true",
        "fiber.dbname": "kenku",
        "fiber.user": "kenku",
        "fiber.secret": "pw",
    }
    job = parse_job("kenku-pg", labels)
    assert isinstance(job, DumpJob)
    assert job.path is None


def test_invalid_cron_is_misconfigured() -> None:
    labels = {
        "fiber.enable": "true",
        "fiber.dbname": "k",
        "fiber.user": "k",
        "fiber.secret": "s",
        "fiber.schedule": "not a cron",
    }
    result = parse_job("kenku-pg", labels)
    assert isinstance(result, MisconfiguredJob)
    assert any("cron" in e for e in result.errors)


def test_mysql_engine_defaults_to_plain_format_and_3306() -> None:
    labels = {
        "fiber.enable": "true",
        "fiber.engine": "mysql",
        "fiber.dbname": "postal",
        "fiber.user": "postal",
        "fiber.secret": "postal_db_password",
    }
    job = parse_job("postal-db", labels)
    assert isinstance(job, DumpJob)
    assert job.engine is Engine.MYSQL
    assert job.fmt is DumpFormat.PLAIN
    assert job.port == 3306


def test_mysql_engine_accepts_directory_format() -> None:
    labels = {
        "fiber.enable": "true",
        "fiber.engine": "mysql",
        "fiber.dbname": "postal",
        "fiber.user": "postal",
        "fiber.secret": "s",
        "fiber.format": "directory",
        "fiber.jobs": "4",
    }
    job = parse_job("postal-db", labels)
    assert isinstance(job, DumpJob)
    assert job.fmt is DumpFormat.DIRECTORY


def test_mysql_custom_format_is_misconfigured() -> None:
    labels = {
        "fiber.enable": "true",
        "fiber.engine": "mysql",
        "fiber.dbname": "postal",
        "fiber.user": "postal",
        "fiber.secret": "s",
        "fiber.format": "custom",
    }
    result = parse_job("postal-db", labels)
    assert isinstance(result, MisconfiguredJob)
    assert any("custom" in e and "mysql" in e for e in result.errors)


def test_default_provider_swarm_accepts_unlabeled() -> None:
    labels = {"fiber.enable": "true", "fiber.dbname": "k", "fiber.user": "k", "fiber.secret": "s"}
    assert isinstance(parse_job("kenku-pg", labels), DumpJob)  # active defaults to swarm


def test_provider_mismatch_is_misconfigured() -> None:
    labels = {"fiber.enable": "true", "fiber.dbname": "k", "fiber.user": "k",
              "fiber.secret": "s", "fiber.provider": "swarm"}
    result = parse_job("e2e-pg", labels, active_provider="docker")
    assert isinstance(result, MisconfiguredJob)
    assert len(result.errors) == 1
    assert "provider mismatch" in result.errors[0]
    assert "label=swarm" in result.errors[0]
    assert "active=docker" in result.errors[0]


def test_docker_provider_label_accepted_when_active() -> None:
    labels = {"fiber.enable": "true", "fiber.dbname": "e2e", "fiber.user": "e2e",
              "fiber.secret": "s", "fiber.provider": "docker"}
    assert isinstance(parse_job("e2e-pg", labels, active_provider="docker"), DumpJob)


# ---------------------------------------------------------------------------
# reconcile — many services at once
# ---------------------------------------------------------------------------

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


def test_reconcile_threads_active_provider() -> None:
    services = {"e2e-pg": {"fiber.enable": "true", "fiber.dbname": "e2e",
                           "fiber.user": "e2e", "fiber.secret": "s", "fiber.provider": "swarm"}}
    jobs, misconfigured, _ = reconcile(services, active_provider="docker")
    assert jobs == []
    assert [m.service for m in misconfigured] == ["e2e-pg"]
    assert "provider mismatch" in misconfigured[0].errors[0]
