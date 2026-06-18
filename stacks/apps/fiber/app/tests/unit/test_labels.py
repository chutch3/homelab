from fiber.labels import parse_job
from fiber.models import DumpJob, DumpFormat, Engine, MisconfiguredJob


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
