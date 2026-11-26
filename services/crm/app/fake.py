"""In-memory CRM adapter for tests and offline demos."""

from app.errors import CrmNotFoundError
from app.models import Account, Opportunity, OpportunityDraft


class FakeCrm:
    """Small in-memory implementation of :class:`CrmPort`."""

    def __init__(
        self,
        accounts: list[Account] | None = None,
        opportunities: list[Opportunity] | None = None,
    ) -> None:
        self.accounts = list(accounts or [])
        self.opportunities = list(opportunities or [])
        self._next_id = 1

    async def search_accounts(self, term: str) -> list[Account]:
        needle = term.casefold()
        return [
            account for account in self.accounts if needle in account.name.casefold()
        ]

    async def search_opportunities(self, term: str) -> list[Opportunity]:
        needle = term.casefold()
        return [
            opportunity
            for opportunity in self.opportunities
            if needle in opportunity.name.casefold()
            or (
                opportunity.account_name
                and needle in opportunity.account_name.casefold()
            )
        ]

    async def create_opportunity(self, draft: OpportunityDraft) -> str:
        account = next(
            (item for item in self.accounts if item.id == draft.account_id), None
        )
        if account is None:
            raise CrmNotFoundError(f"Account not found: {draft.account_id}")
        record_id = f"fake-{self._next_id}"
        self._next_id += 1
        self.opportunities.append(
            Opportunity(
                id=record_id,
                name=draft.name,
                account_id=draft.account_id,
                account_name=account.name,
                amount=draft.amount,
                close_date=draft.close_date,
                stage_name=draft.stage_name,
            )
        )
        return record_id

    async def get_opportunity(self, opportunity_id: str) -> Opportunity:
        for opportunity in self.opportunities:
            if opportunity.id == opportunity_id:
                return opportunity
        raise CrmNotFoundError(f"Opportunity not found: {opportunity_id}")

    async def update_opportunity(
        self, opportunity_id: str, changes: dict[str, object]
    ) -> None:
        allowed = {"name", "amount", "close_date", "stage_name"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unsupported opportunity fields: {sorted(unknown)}")
        for index, opportunity in enumerate(self.opportunities):
            if opportunity.id == opportunity_id:
                values = opportunity.model_dump()
                values.update(changes)
                self.opportunities[index] = Opportunity.model_validate(values)
                return
        raise CrmNotFoundError(f"Opportunity not found: {opportunity_id}")
