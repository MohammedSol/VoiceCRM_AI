#!/usr/bin/env pwsh
# scripts/up.ps1 — Equivalent de `make up` pour Windows sans make
param([switch]$Build = $true)

$env:COMPOSE_FILE = "docker-compose.yml"
if ($Build) {
    docker compose up --build -d
} else {
    docker compose up -d
}
