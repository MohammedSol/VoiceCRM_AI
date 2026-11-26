# Shared contracts

This package contains small, stable Python interfaces shared across service boundaries.
Sprint 2 introduces `CrmPort` and immutable `CrmOpportunityDraft` in
`src/voicecrm_contracts/crm.py`; the backend depends on the protocol rather than importing
implementation code from `services/crm`.

The package is intentionally limited to contracts. HTTP request/response models remain in
the owning service unless another service needs the exact schema.
