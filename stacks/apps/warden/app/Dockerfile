FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY app/pyproject.toml app/uv.lock ./
RUN uv sync --no-dev --no-install-project
COPY app/warden /app/warden
RUN mkdir -p /state
EXPOSE 9090
CMD ["uv", "run", "python", "-m", "warden.main"]
