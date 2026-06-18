from datetime import datetime, timezone

from fiber.services.registry_state import RegistryState, Snapshot


def test_defaults_empty_then_updates() -> None:
    rs = RegistryState()
    assert rs.get().jobs == [] and rs.get().misconfigured == []
    snap = Snapshot(
        jobs=["j"],  # type: ignore
        misconfigured=["m"],  # type: ignore
        skipped=[("traefik", "no fiber.enable")],
    )
    rs.set(snap)
    assert rs.get() is snap


def test_snapshot_has_scanned_at_default_none() -> None:
    snap = Snapshot()
    assert snap.scanned_at is None
    assert snap.error is None


def test_snapshot_scanned_at_and_error_stored() -> None:
    now = datetime(2026, 6, 16, 9, 0, tzinfo=timezone.utc)
    snap = Snapshot(scanned_at=now, error=None)
    assert snap.scanned_at == now
    snap_err = Snapshot(scanned_at=now, error="docker unavailable")
    assert snap_err.error == "docker unavailable"
