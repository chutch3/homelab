# Dockerfile for Worker Service
FROM python:3.10-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only pyproject.toml and uv.lock to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev --no-install-project

COPY . .

CMD ["python", "main.py"]
