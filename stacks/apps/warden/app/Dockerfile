FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY app/pyproject.toml app/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY app/warden /app/warden
RUN uv sync --locked --no-dev --no-editable \
    && mkdir -p /state
EXPOSE 9090
ENTRYPOINT ["/app/.venv/bin/warden"]
CMD ["serve"]
