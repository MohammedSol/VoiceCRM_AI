"""Backend CRM boundary and explicitly opt-in development fake."""

from __future__ import annotations

from voicecrm_contracts import CrmOpportunityDraft


class CrmUnavailableError(Exception):
    """Raised when no CRM implementation is configured."""


class UnconfiguredCrm:
    async def create_opportunity(self, draft: CrmOpportunityDraft) -> str:
        del draft
        raise CrmUnavailableError("No CRM adapter is configured")


class FakeCrm:
    """In-memory CRM adapter for explicitly selected offline demos and tests."""

    def __init__(self) -> None:
        self.created: list[tuple[str, CrmOpportunityDraft]] = []

    async def create_opportunity(self, draft: CrmOpportunityDraft) -> str:
        record_id = f"006FAKE{len(self.created) + 1:09d}"
        self.created.append((record_id, draft))
        return record_id
