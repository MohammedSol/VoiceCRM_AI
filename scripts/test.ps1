#!/usr/bin/env pwsh
# scripts/test.ps1 — Equivalent de `make test`

Set-Location "$PSScriptRoot\..\services\backend"
uv run pytest tests/ ../../packages/validation/tests/ -v
