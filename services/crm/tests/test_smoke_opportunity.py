"""Tests that the live create smoke check requires explicit confirmation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app import smoke_opportunity
from app.models import Account, Opportunity, OpportunityDraft
from app.salesforce import SalesforceSettings


class StubCrm:
    created = False

    def __init__(self, _: SalesforceSettings) -> None:
        pass

    async def __aenter__(self) -> StubCrm:
        return self

    async def __aexit__(self, *_: object) -> None:
        pass

    async def search_accounts(self, _: str) -> list[Account]:
        return [Account(id="001000000000001AAA", name="Acme Test")]

    async def create_opportunity(self, _: OpportunityDraft) -> str:
        self.created = True
        return "006000000000001AAA"

    async def get_opportunity(self, opportunity_id: str) -> Opportunity:
        return Opportunity(
            id=opportunity_id,
            name="CRM Sprint 1 smoke test",
            account_id="001000000000001AAA",
            amount=Decimal("10000"),
            close_date=date(2027, 3, 31),
            stage_name="Qualification",
        )


@pytest.mark.asyncio
async def test_smoke_does_not_write_without_exact_confirmation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stub = StubCrm(SalesforceSettings(client_id="id", client_secret="secret"))
    monkeypatch.setattr(
        smoke_opportunity.SalesforceSettings,
        "from_env",
        classmethod(
            lambda cls: SalesforceSettings(client_id="id", client_secret="secret")
        ),
    )
    monkeypatch.setattr(smoke_opportunity, "SalesforceCrm", lambda _: stub)
    monkeypatch.setattr("builtins.input", lambda _: "NO")

    result = await smoke_opportunity.run_smoke(
        "Acme Test", Decimal("10000"), date(2027, 3, 31), "Qualification"
    )

    assert result == 3
    assert not stub.created
    assert "aucune opportunité n'a été créée" in capsys.readouterr().out
