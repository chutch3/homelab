"""Alembic wiring; database URL is supplied by the caller/environment."""

import os

from alembic import context
from sqlalchemy import create_engine

url = context.config.attributes.get("database_url") or os.environ["DISKTRACKER_DATABASE_URL"]
engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
