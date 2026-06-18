import pytest

from fiber.config import Config


def test_provider_defaults_to_swarm(monkeypatch) -> None:
    monkeypatch.delenv("FIBER_PROVIDER", raising=False)
    from fiber.config import Config
    assert Config.from_env().provider == "swarm"


def test_provider_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("FIBER_PROVIDER", "docker")
    from fiber.config import Config
    assert Config.from_env().provider == "docker"


def test_invalid_provider_raises(monkeypatch) -> None:
    monkeypatch.setenv("FIBER_PROVIDER", "swarmm")
    with pytest.raises(ValueError, match="FIBER_PROVIDER must be"):
        Config.from_env()


def test_from_env_uses_defaults_and_overrides(monkeypatch) -> None:
    monkeypatch.setenv("FIBER_BOWL_PATH", "/mnt/bowl")
    monkeypatch.setenv("FIBER_MAX_CONCURRENT_MOVEMENTS", "3")
    cfg = Config.from_env()
    assert cfg.bowl_path == "/mnt/bowl"
    assert cfg.max_concurrent == 3
    assert cfg.metrics_port == 9090           # default
    assert cfg.scan_interval == 60.0          # default


def test_scan_enabled_defaults_to_true(monkeypatch) -> None:
    monkeypatch.delenv("FIBER_SCAN_ENABLED", raising=False)
    cfg = Config.from_env()
    assert cfg.scan_enabled is True


@pytest.mark.parametrize("value", ["0", "false", "False", "FALSE", "no", "No", "NO"])
def test_scan_enabled_false_for_falsy_strings(monkeypatch, value: str) -> None:
    monkeypatch.setenv("FIBER_SCAN_ENABLED", value)
    cfg = Config.from_env()
    assert cfg.scan_enabled is False


@pytest.mark.parametrize("value", ["1", "true", "True", "yes", "YES"])
def test_scan_enabled_true_for_truthy_strings(monkeypatch, value: str) -> None:
    monkeypatch.setenv("FIBER_SCAN_ENABLED", value)
    cfg = Config.from_env()
    assert cfg.scan_enabled is True
