from fiber.domain.models import DumpJob, Engine, DumpFormat


def _job(**over: object) -> DumpJob:
    base = dict(
        service="kenku-pg", engine=Engine.POSTGRES, host="kenku-pg", port=5432,
        dbname="kenku", user="kenku", secret="kenku_db_password",
        schedule="0 3 * * *", options=(), retain=7, fmt=DumpFormat.CUSTOM,
        jobs=1, timeout=None, app=None, schema_version_query=None,
    )
    base.update(over)
    return DumpJob(**base)  # type: ignore[arg-type]


def test_bowl_key_is_the_service_name() -> None:
    assert _job(service="immich-pg").bowl_key == "immich-pg"
