"""Monorepo CI/build tooling for the homelab repo.

A standalone project (``tools/ci``) installed editable by the root ``pyproject.toml``
so it imports as ``ci`` in CI, pre-commit, and local runs. Home for change detection
(:mod:`ci.affected`) and future build/validate helpers.
"""
