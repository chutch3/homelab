# The collector: the collection loop and, beside it, the API that previews sources.
# Build context: stacks/apps/disktracker (the collector needs listing_text/).

FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/collector
# listing_text is a path dependency of the collector (../listing_text), installed editable.
COPY listing_text /app/listing_text
COPY collector/pyproject.toml collector/uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/collector/.venv/bin:$PATH"
COPY collector/collector ./collector
# The client generated from the backend's OpenAPI spec (scripts/generate-api-client.sh).
COPY collector/disktracker_api ./disktracker_api
EXPOSE 8100
CMD ["python", "-m", "collector"]
