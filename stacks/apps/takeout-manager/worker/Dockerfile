# Dockerfile for Worker Service
FROM python:3.10-slim

# Install poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copy only pyproject.toml and poetry.lock to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install dependencies (without the project itself, since code isn't copied yet)
RUN poetry config virtualenvs.create false && \
    poetry install --without dev --no-root --no-interaction --no-ansi

COPY . .

CMD ["python", "main.py"]
