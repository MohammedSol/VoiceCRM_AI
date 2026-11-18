# syntax=docker/dockerfile:1
# Sprint 1 — Dockerfile squelette (connecteur CRM, non implémenté)
# Build context: repository root
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.1
COPY services/crm/pyproject.toml services/crm/uv.lock ./
RUN uv sync --frozen --no-dev
COPY packages/ /packages/
COPY services/crm/app/ ./app/

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8002
CMD ["python", "-m", "app"]
