# Dockerfile for Worker Service
FROM python:3.12-slim-bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

# Google Photos Takeout Helper (Neo) — pinned release + checksum verification.
# Bump both together: https://github.com/Xentraxx/GooglePhotosTakeoutHelper_Neo/releases
ARG GPTH_VERSION=6.1.8
ARG GPTH_SHA256=9608ef1327ba6817acd8479da2bf201e544fa8fdf89e3f0e203c5ab091c22e9a
RUN curl -fsSL -o /usr/local/bin/gpth \
    "https://github.com/Xentraxx/GooglePhotosTakeoutHelper_Neo/releases/download/v${GPTH_VERSION}/gpth_neo-${GPTH_VERSION}-release-linux-x64.bin" \
    && echo "${GPTH_SHA256}  /usr/local/bin/gpth" | sha256sum -c - \
    && chmod +x /usr/local/bin/gpth

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only pyproject.toml and uv.lock to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev --no-install-project

COPY . .

# Runs as PUID:PGID (docker-compose `user:`) to match the CIFS mounts' uid/gid —
# give that uid a writable HOME so uv's cache dir doesn't fall back to /.cache.
# /staging is pre-created with the same ownership: Docker copies an image
# directory's contents (incl. ownership) into a fresh named volume on its first
# mount, so this is what makes the empty takeout-staging volume writable by 1000.
RUN mkdir -p /home/worker /staging && chown -R 1000:1000 /app /home/worker /staging
ENV HOME=/home/worker

CMD ["uv", "run", "python", "main.py"]
