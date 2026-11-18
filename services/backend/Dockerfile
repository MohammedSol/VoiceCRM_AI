# syntax=docker/dockerfile:1
# Build context: repository root (to allow COPY packages/)
FROM python:3.12-slim AS base

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv==0.11.1

# Copy dependency files first (layer cache)
COPY services/backend/pyproject.toml services/backend/uv.lock ./

# Install production dependencies only
RUN uv sync --frozen --no-dev

# Copy shared packages
COPY packages/ /packages/

# Copy application code
COPY services/backend/app/ ./app/

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
