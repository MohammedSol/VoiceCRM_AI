# syntax=docker/dockerfile:1
# Sprint 3 — Dockerfile squelette (agent LangGraph, non implémenté)
# Build context: repository root
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.1
COPY services/agent/pyproject.toml services/agent/uv.lock ./
RUN uv sync --frozen --no-dev
COPY packages/ /packages/
COPY services/agent/app/ ./app/

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8001
CMD ["python", "-m", "app"]
