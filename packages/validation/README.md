# Deterministic validation

This pure Python package validates opportunity drafts without database, web-framework or CRM
I/O. `validate_opportunity` returns a validated value plus stable field-level error codes.
The caller supplies the configured amount ceiling and the exact Salesforce stages for its
organization. Amounts are parsed as `Decimal` and never pass through binary floating point.

Run its unit tests from `services/backend` with:

```powershell
uv run pytest ../../packages/validation/tests/ -v
```
