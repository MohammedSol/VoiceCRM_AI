"""Typed boundary contract used by the backend and CRM adapters."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class CrmOpportunityDraft:
    name: str
    account_id: str
    account_name: str
    amount: Decimal
    close_date: date
    stage_name: str


class CrmPort(Protocol):
    async def create_opportunity(self, draft: CrmOpportunityDraft) -> str: ...
