# syntax=docker/dockerfile:1
# Build context: repository root (to allow COPY packages/)
FROM python:3.12-slim AS base

WORKDIR /workspace

# Install uv
RUN pip install --no-cache-dir uv==0.11.1

# Copy local shared packages before resolving path dependencies
COPY packages/contracts/ ./packages/contracts/
COPY packages/validation/ ./packages/validation/

# Copy dependency files and install production dependencies
COPY services/backend/pyproject.toml services/backend/uv.lock ./services/backend/
WORKDIR /workspace/services/backend
RUN uv sync --frozen --no-dev

# Copy application code and migration assets
COPY services/backend/app/ ./app/
COPY services/backend/alembic.ini ./alembic.ini
COPY services/backend/alembic/ ./alembic/

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /workspace/services/backend
USER appuser

ENV PATH="/workspace/services/backend/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
