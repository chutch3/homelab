# Dockerfile for Worker Service
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only pyproject.toml and uv.lock to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev --no-install-project

COPY . .

# Runs as PUID:PGID (docker-compose `user:`) to match the CIFS mounts' uid/gid —
# give that uid a writable HOME so uv's cache dir doesn't fall back to /.cache.
RUN mkdir -p /home/worker && chown -R 1000:1000 /app /home/worker
ENV HOME=/home/worker

CMD ["uv", "run", "python", "main.py"]
