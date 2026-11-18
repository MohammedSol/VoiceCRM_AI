# ============================================================
# Makefile — Opportunity Voice Assistant
# Cible principale pour la CI Linux/macOS et reference locale.
# Sur Windows sans make : utiliser scripts/ps/*.ps1 (equiv. PowerShell).
# ============================================================

.PHONY: help up down test lint pre-commit build clean

# Variables
COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Lance tous les services (build si nécessaire)
	$(COMPOSE) -f $(COMPOSE_FILE) up --build -d

down: ## Arrête et supprime les conteneurs
	$(COMPOSE) -f $(COMPOSE_FILE) down

build: ## Build les images Docker sans démarrer
	$(COMPOSE) -f $(COMPOSE_FILE) build

test: ## Lance pytest sur le backend (et futurs services)
	cd services/backend && uv run pytest tests/ -v

lint: ## Lance ruff + mypy sur le backend
	cd services/backend && uv run ruff check app/ tests/
	cd services/backend && uv run ruff format --check app/ tests/
	cd services/backend && uv run mypy app/

pre-commit: ## Lance pre-commit sur tous les fichiers
	pre-commit run --all-files

clean: ## Supprime les volumes Docker
	$(COMPOSE) -f $(COMPOSE_FILE) down -v

logs: ## Affiche les logs de tous les services
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f
