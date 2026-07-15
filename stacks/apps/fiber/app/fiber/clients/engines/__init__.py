from __future__ import annotations

from fiber.clients.engines.base import DumpEngine
from fiber.clients.engines.mysql import MysqlEngine
from fiber.clients.engines.postgres import PostgresEngine
from fiber.domain.models import Engine


def build_default_engines() -> dict[Engine, DumpEngine]:
    return {Engine.POSTGRES: PostgresEngine(), Engine.MYSQL: MysqlEngine()}


__all__ = ["DumpEngine", "MysqlEngine", "PostgresEngine", "build_default_engines"]
