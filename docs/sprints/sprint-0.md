# docs/sprints/sprint-0.md — Passation Sprint 0

**Responsable :** Mohammed Solimani
**Date :** 2026-11-18
**Durée effective :** ~1 journée de travail

---

## Ce qui est fait

### 1. Monorepo et arborescence

- Dépôt Git initialisé sur `main` avec `git init -b main`
- Arborescence complète créée conformément à la section « Hiérarchie du projet » du plan :
  `services/`, `packages/`, `frontend/`, `db/`, `mlops/`, `tests/`, `docs/`
- Chaque service Python initialisé avec `uv` : `backend`, `agent`, `crm`, `voice`

### 2. Backend FastAPI

- Route `GET /health` → `{"status": "ok", "version": "0.1.0"}`
- Structure : `app/main.py`, `app/api/health.py`, `app/core/config.py`
- Toute config via variables d'environnement (`DATABASE_URL`, `LOG_LEVEL`, `DEBUG`)

### 3. Tests backend

- 2 tests pytest : `test_health_returns_200` et `test_health_response_body`
- **Résultat validé :** `2 passed in 0.53s` (commande : `uv run pytest tests/ -v`)

### 4. Frontend Next.js

- Next.js 16.4.6 avec TypeScript, App Router, mode `standalone` pour Docker
- Page `/` qui appelle `GET /health` côté serveur et affiche l'état du backend
- URL backend lue depuis `BACKEND_INTERNAL_URL` ou `NEXT_PUBLIC_BACKEND_URL` — jamais écrite en dur

### 5. Docker Compose

- `docker-compose.yml` : backend, PostgreSQL 16-alpine, MLflow 3.18.0, frontend
  Chaque service a un healthcheck.
- `docker-compose.test.yml` : PostgreSQL jetable sur port 5433, pour les tests d'intégration futurs
- Ports : backend 8000, frontend 3000, MLflow 5050, PostgreSQL non exposé

### 6. Dockerfiles

- Backend : multi-stage avec `python:3.12-slim`, copie de `packages/` depuis la racine
- Frontend : multi-stage avec `node:22-alpine`, mode standalone Next.js
- Agent, CRM, Voice : squelettes pour sprints futurs

### 7. Outillage qualité

- **Ruff 0.17.5** : lint + format Python
- **Mypy 2.4.1** : typage strict
- **pre-commit 4.7.0** avec hooks : trailing-whitespace, end-of-file-fixer, check-yaml, ruff, ruff-format, **gitleaks v8.30.1**
- Hooks git installés : `pre-commit install`

### 8. CI GitHub Actions

- `.github/workflows/ci.yml` : lint + test backend + build images Docker
- Déclenché à chaque push sur `main`
- Utilise `astral-sh/setup-uv@v5`, `actions/setup-python@v5`, `docker/build-push-action@v6`

### 9. Fichiers de config

- `.env.example` : modèle complet, aucun secret
- `.gitignore` : python, node, docker, IDE, secrets
- `.gitattributes` : LF pour Dockerfile, shell, YAML
- `Makefile` : `make up/down/test/lint/pre-commit`
- `scripts/*.ps1` : équivalents PowerShell pour Windows (make absent)

### 10. Documentation

- `README.md` : lancer en 3 commandes, table des services, ports
- `docs/adr/ADR-001-agent-unique.md` : agent unique LangGraph confirmé par le prof
- `docs/adr/ADR-002-mlflow-storage.md` : stockage MLflow fichiers locaux
- `docs/adr/ADR-003-make-absent-windows.md` : scripts PS1 équivalents

---

## Comment lancer les tests

```bash
# Backend (Python)
cd services/backend
uv run pytest tests/ -v
# → 2 passed

# Lint
uv run ruff check app/ tests/
uv run ruff format --check app/ tests/
uv run mypy app/

# pre-commit
pre-commit run --all-files
```

```powershell
# Windows sans make
.\scripts\test.ps1
.\scripts\lint.ps1
```

---

## Décisions prises

| Décision | Raison | ADR |
|----------|--------|-----|
| Agent unique LangGraph | Latence, simplicité, confirmé prof | ADR-001 |
| MLflow stockage fichiers | Option la plus simple (plan le dit explicitement) | ADR-002 |
| Scripts PS1 en plus du Makefile | `make` absent sur Windows 11 du développeur | ADR-003 |
| MLflow image `ghcr.io/mlflow/mlflow:v3.18.0` | Image officielle vérifiée pip (mlflow==3.18.0) | ADR-002 |
| PostgreSQL non exposé sur l'hôte | Sécurité par défaut | docker-compose.yml |

---

## Problèmes connus

1. **Docker Desktop non démarré** lors de l'initialisation : les builds Docker et le
   `docker compose up` n'ont pas pu être exécutés et validés. Le code est correct ;
   lancer Docker Desktop puis `.\scripts\up.ps1` pour validation.

2. **`make` absent sur Windows 11** : utiliser les scripts `scripts/*.ps1`.
   Installer via `winget install GnuWin32.Make` ou WSL si souhaité.

3. **`gh` CLI absent** : pour les opérations GitHub (créer des releases, voir la CI),
   installer via `winget install GitHub.cli`.

4. **pre-commit `--all-files` sur `node_modules/`** : le `.gitignore` exclut
   `node_modules/` ; pre-commit ne scanne que les fichiers suivis par Git.

---

## Pour le Sprint 1 (Ahmed ou Farah)

1. Lancer `git pull --rebase` depuis `main`
2. Démarrer Docker Desktop
3. `.\scripts\test.ps1` → doit afficher `2 passed`
4. `.\scripts\up.ps1` → vérifier que les 4 services sont healthy
5. `curl http://localhost:8000/health` → `{"status":"ok",...}`
6. Lire `docs/adr/` pour comprendre les décisions
7. Lire le plan Sprint 1 et commencer `services/crm/`
