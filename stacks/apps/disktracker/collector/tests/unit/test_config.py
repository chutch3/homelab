import pytest

from collector.config import Config


def test_only_the_disktracker_url_is_required() -> None:
    assert Config.from_env({"DISKTRACKER_URL": "http://disktracker:8000/"}) == Config(
        disktracker_url="http://disktracker:8000",
        min_delay_seconds=2.0,
        run_once=False,
        poll_seconds=60.0,
        retry_delay_seconds=0.5,
        log_level="INFO",
    )


def test_every_setting_can_be_overridden() -> None:
    environ = {
        "DISKTRACKER_URL": "http://d",
        "COLLECTOR_MIN_DELAY_SECONDS": "5",
        "COLLECTOR_RUN_ONCE": "1",
        "COLLECTOR_POLL_SECONDS": "5",
        "COLLECTOR_RETRY_DELAY_SECONDS": "0",
        "LOG_LEVEL": "debug",
        "FLARESOLVERR_URL": "http://flaresolverr:8191/",
        "COLLECTOR_PROXY_URL": "http://vpn:8888/",
        "COLLECTOR_API_PORT": "8100",
        "COLLECTOR_PREVIEW_SECONDS": "30",
    }
    assert Config.from_env(environ) == Config(
        disktracker_url="http://d",
        min_delay_seconds=5.0,
        run_once=True,
        poll_seconds=5.0,
        retry_delay_seconds=0.0,
        log_level="DEBUG",
        flaresolverr_url="http://flaresolverr:8191",
        proxy_url="http://vpn:8888",
        api_port=8100,
        preview_seconds=30.0,
    )


def test_an_unknown_log_level_is_refused_at_startup() -> None:
    with pytest.raises(ValueError, match="Unknown LOG_LEVEL: CHATTY"):
        Config.from_env({"DISKTRACKER_URL": "http://d", "LOG_LEVEL": "chatty"})
