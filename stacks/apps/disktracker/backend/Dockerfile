# The web service: the API, which also serves the built frontend.
# Build context: stacks/apps/disktracker (the backend needs frontend/ and listing_text/).

FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/backend
# listing_text is a path dependency of the backend (../listing_text), installed editable.
COPY listing_text /app/listing_text
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/backend/.venv/bin:$PATH"
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY backend/disktracker ./disktracker
COPY --from=frontend /frontend/dist /app/site
ENV DISKTRACKER_STATIC_DIR=/app/site
EXPOSE 8000
# Migrations run before the API starts, so a deploy of a new version brings its schema along.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn disktracker.main:app --host 0.0.0.0 --port 8000"]
