FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Postgres client majors 14/15/16 for version-matched pg_dump (see spec §18)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends postgresql-client-14 postgresql-client-15 postgresql-client-16 \
    && apt-get install -y --no-install-recommends mariadb-client mydumper \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app/pyproject.toml app/uv.lock ./
RUN uv sync --no-dev --no-install-project
COPY app/fiber /app/fiber
RUN mkdir -p /backups /state
EXPOSE 9090
CMD ["uv", "run", "python", "-m", "fiber.main"]
