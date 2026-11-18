# Opportunity Voice Assistant

Assistant vocal intelligent pour la gestion des opportunités CRM Salesforce.
Projet étudiant – 10 sprints, équipe de 3.

## Lancer le projet en 3 commandes

```bash
# 1. Copier et configurer les variables d'environnement
cp .env.example .env
# Éditez .env : renseignez POSTGRES_PASSWORD

# 2. Démarrer tous les services
docker compose up --build -d
# (Windows sans make) : .\scripts\up.ps1

# 3. Vérifier que tout est opérationnel
curl http://localhost:8000/health
# → {"status":"ok","version":"0.1.0"}
# Ouvrir http://localhost:3000 dans le navigateur
```

## Services et ports

| Service    | URL locale                    | Description                     |
|------------|-------------------------------|---------------------------------|
| Backend    | http://localhost:8000         | FastAPI – route `/health`, `/docs` |
| Frontend   | http://localhost:3000         | Next.js – affiche le statut backend |
| MLflow UI  | http://localhost:5050         | Suivi des évaluations (Sprint 3+) |
| PostgreSQL | interne uniquement (port 5432)| Non exposé sur l'hôte            |

> **Note ports :** choix documenté dans [ADR-002](docs/adr/ADR-002-mlflow-storage.md).
> PostgreSQL non exposé sur l'hôte par défaut (sécurité).

## Commandes utiles

```bash
# Linux/macOS avec make
make up       # lance les services
make down     # arrête les services
make test     # pytest backend
make lint     # ruff + mypy

# Windows sans make (PowerShell)
.\scripts\up.ps1
.\scripts\down.ps1
.\scripts\test.ps1
.\scripts\lint.ps1

# pre-commit (après installation)
pre-commit install
pre-commit run --all-files
```

## Architecture

Monorepo — un service, un Dockerfile, ses propres tests.
Les services communiquent uniquement par API (jamais d'import croisé de code).

```
services/backend/   ← FastAPI (Sprint 0 : /health)
services/agent/     ← LangGraph (Sprint 3)
services/crm/       ← Connecteur Salesforce (Sprint 1)
services/voice/     ← STT + TTS (Sprint 5)
packages/           ← Schémas, validation, sécurité partagés
frontend/           ← Next.js (Sprint 7, page /health pour Sprint 0)
```

Voir [docs/adr/](docs/adr/) pour toutes les décisions d'architecture.

## Développement local (backend sans Docker)

```bash
cd services/backend
uv sync
uv run uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

## Tests

```bash
cd services/backend
uv run pytest tests/ -v
# → 2 passed (test /health)
```

## Sprints

| Sprint | Tag Git        | Statut   |
|--------|---------------|----------|
| 0      | sprint-0-ok   | 🚧 En cours |
| 1-9    | —             | À faire  |
