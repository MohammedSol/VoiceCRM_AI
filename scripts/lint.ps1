#!/usr/bin/env pwsh
# scripts/lint.ps1 — Equivalent de `make lint`

Set-Location "$PSScriptRoot\..\services\backend"
Write-Host "=== ruff check ==="
uv run ruff check app/ tests/
Write-Host "=== ruff format --check ==="
uv run ruff format --check app/ tests/
Write-Host "=== mypy ==="
uv run mypy app/
Write-Host "Lint terminé."
