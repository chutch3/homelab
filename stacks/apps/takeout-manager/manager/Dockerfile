# Multi-stage Dockerfile for Manager Service

# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Build Backend
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only pyproject.toml and uv.lock to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY ./backend /app/backend

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend/dist /app/backend/static

# Create db directory
RUN mkdir -p /app/db

EXPOSE 8000

CMD ["uvicorn", "backend.application:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
