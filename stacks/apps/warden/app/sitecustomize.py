# Enables coverage measurement in subprocesses spawned by the integration harness.
# No-op in production: coverage is a dev-only dependency and COVERAGE_PROCESS_START
# is unset, so the import simply fails and is ignored.
try:  # pragma: no cover
    import coverage

    coverage.process_startup()
except Exception:  # pragma: no cover
    pass
