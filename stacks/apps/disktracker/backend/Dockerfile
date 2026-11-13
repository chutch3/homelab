# The web service: the API, which also serves the built frontend.
# Build context: stacks/apps/disktracker (the backend needs frontend/ and packages/listing_facts/).

FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/backend
# listing_facts is a path dependency of the backend (../packages/listing_facts), installed editable.
COPY packages/listing_facts /app/packages/listing_facts
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
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn disktracker.main:create_app --factory --host 0.0.0.0 --port 8000"]
