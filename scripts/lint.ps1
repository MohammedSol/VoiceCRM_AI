#!/usr/bin/env pwsh
# scripts/lint.ps1 — Equivalent de `make lint`

Set-Location "$PSScriptRoot\..\services\backend"
Write-Host "=== ruff check ==="
uv run ruff check app/ tests/ alembic/ ../../packages/contracts/src/ ../../packages/validation/src/ ../../packages/validation/tests/
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== ruff format --check ==="
uv run ruff format --check app/ tests/ alembic/ ../../packages/contracts/src/ ../../packages/validation/src/ ../../packages/validation/tests/
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== mypy ==="
uv run mypy app/ ../../packages/contracts/src/ ../../packages/validation/src/
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Lint terminé."
