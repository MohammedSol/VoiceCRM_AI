"""CRM adapter contract shared by real and fake implementations."""

from typing import Protocol

from app.models import Account, Opportunity, OpportunityDraft


class CrmPort(Protocol):
    """Async operations required by the assistant's CRM layer."""

    async def search_accounts(self, term: str) -> list[Account]: ...

    async def search_opportunities(self, term: str) -> list[Opportunity]: ...

    async def create_opportunity(self, draft: OpportunityDraft) -> str: ...

    async def get_opportunity(self, opportunity_id: str) -> Opportunity: ...

    async def update_opportunity(
        self, opportunity_id: str, changes: dict[str, object]
    ) -> None: ...
