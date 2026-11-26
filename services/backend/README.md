# Backend — Opportunity Voice Assistant

FastAPI service for session creation and the opportunity prepare/confirm/cancel workflow.
Sprint 2 adds PostgreSQL persistence, Alembic migrations, deterministic validation and an
idempotent action state machine.

## Local development on Windows

Start PostgreSQL from the repository root with Docker Compose if it is not already running:

```powershell
docker compose up -d db
```

Compose publishes PostgreSQL on host port `5433` (container port `5432`). From
`services/backend`, use the host address for commands running on Windows:

```powershell
uv sync --group dev
$env:DATABASE_URL = "postgresql://postgres:<your-local-password>@localhost:5433/voicecrm"
uv run alembic upgrade head
$env:CRM_DRIVER = "fake"
uv run uvicorn app.main:app --reload
```

Inside Docker Compose, the backend uses `db:5432`. Migrations are explicit; the application
never calls `create_all()` at startup. Apply migrations before using workflow routes.

OpenAPI is at <http://localhost:8000/docs>; `GET /health` remains available without a
PostgreSQL query.

## Workflow API

1. `POST /v1/sessions` creates a session.
2. `POST /v1/sessions/{session_id}/actions/prepare` validates and stores a draft. Supply an
   `Idempotency-Key` header (8–128 characters). The response contains a confirmation summary
   and an expiring action ID.
3. `POST /v1/actions/{action_id}/confirm` is the only route that calls the CRM port.
4. `POST /v1/actions/{action_id}/cancel` cancels a still-prepared action.

A prepared action can be confirmed only once. A confirmed retry returns the stored CRM ID;
processing, canceled, failed and expired actions cannot create a second record. A database
claim is committed before the external CRM call. As with any remote system, a process crash
after CRM success but before local result persistence is ambiguous; this implementation
prevents a retry from creating another record and leaves reconciliation as an operational
follow-up.

## CRM adapter boundary

The backend depends on the shared `voicecrm_contracts.CrmPort` interface and never imports
code from `services/crm`. Set `CRM_DRIVER=fake` for an explicit offline demo. The default is
`unconfigured`, which returns a safe `503` on confirm rather than silently simulating a real
write. The Salesforce connector currently remains a separate Sprint 1 component; wiring it
through an API or a separately packaged adapter is still required before this backend can
create a live Salesforce record. Tests inject `FakeCrm` directly.

## Validation and privacy

`packages/validation` validates decimal amounts without converting through float, the
configured ceiling (`MAX_OPPORTUNITY_AMOUNT`), non-past ISO dates, required account/name
fields, and exact allowed Salesforce stages (`SALESFORCE_ALLOWED_STAGES`, comma-separated;
default `Qualification`). Configure stages from the target Salesforce org.

Audit records and structured JSON logs contain only allowlisted identifiers, event/outcome,
duration and error codes—not names, amounts or request bodies. The pending-action payload is
retained in PostgreSQL to support confirmation and is not encrypted in this sprint; do not use
real customer data until the planned encryption/retention work is completed.

## Tests and migrations

From `services/backend`:

```powershell
uv run pytest tests/ -v
uv run ruff check app tests
uv run mypy app tests
uv run alembic upgrade head
```

The API suite uses isolated SQLite databases for fast workflow tests. The initial Alembic
migration has also been verified with PostgreSQL 16 through upgrade → downgrade → upgrade.
Use a disposable database for any downgrade test; downgrading removes all Sprint 2 tables.
