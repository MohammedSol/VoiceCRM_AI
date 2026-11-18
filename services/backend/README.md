# Backend — Opportunity Voice Assistant

Service FastAPI — sessions, routes `/v1`, schéma OpenAPI.

## Sprint 0

Route `GET /health` opérationnelle. Voir `app/api/health.py`.

## Développement local

```bash
uv sync
uv run uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

## Tests

```bash
uv run pytest tests/ -v
```
