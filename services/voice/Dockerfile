# syntax=docker/dockerfile:1
# Sprint 5 — Dockerfile squelette (voice STT+TTS, non implémenté)
# Build context: repository root
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.1
COPY services/voice/pyproject.toml services/voice/uv.lock ./
RUN uv sync --frozen --no-dev
COPY packages/ /packages/
COPY services/voice/app/ ./app/

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8003
CMD ["python", "-m", "app"]
