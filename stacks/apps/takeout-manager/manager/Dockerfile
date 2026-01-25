# Multi-stage Dockerfile for Manager Service

# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Build Backend
FROM python:3.10-slim

# Install poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copy only pyproject.toml and poetry.lock to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install dependencies (without the project itself, since code isn't copied yet)
RUN poetry config virtualenvs.create false && \
    poetry install --without dev --no-root --no-interaction --no-ansi

# Copy application code
COPY ./backend /app/backend

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend/dist /app/backend/static

# Create db directory
RUN mkdir -p /app/db

EXPOSE 8000

CMD ["uvicorn", "backend.application:app", "--host", "0.0.0.0", "--port", "8000"]
