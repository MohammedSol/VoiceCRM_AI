"""Contract and behavior checks for the offline CRM adapter."""

from datetime import date
from decimal import Decimal

import pytest

from app.errors import CrmNotFoundError
from app.fake import FakeCrm
from app.models import Account, Opportunity, OpportunityDraft


@pytest.mark.asyncio
async def test_fake_search_create_read_and_update() -> None:
    crm = FakeCrm(accounts=[Account(id="001-test", name="Atlas Medical")])
    assert await crm.search_accounts("atlas") == [
        Account(id="001-test", name="Atlas Medical")
    ]

    draft = OpportunityDraft(
        name="Renewal",
        account_id="001-test",
        amount=Decimal("1250.50"),
        close_date=date(2027, 6, 30),
        stage_name="Qualification",
    )
    record_id = await crm.create_opportunity(draft)
    created = await crm.get_opportunity(record_id)
    assert created.account_name == "Atlas Medical"
    assert created.amount == Decimal("1250.50")
    assert await crm.search_opportunities("atlas") == [created]

    await crm.update_opportunity(record_id, {"amount": Decimal("2000")})
    assert (await crm.get_opportunity(record_id)).amount == Decimal("2000")


@pytest.mark.asyncio
async def test_fake_rejects_unknown_account_and_missing_opportunity() -> None:
    crm = FakeCrm()
    draft = OpportunityDraft(
        name="Renewal",
        account_id="001-missing",
        amount=Decimal("100"),
        close_date=date(2027, 6, 30),
        stage_name="Qualification",
    )
    with pytest.raises(CrmNotFoundError):
        await crm.create_opportunity(draft)
    with pytest.raises(CrmNotFoundError):
        await crm.get_opportunity("does-not-exist")


def test_opportunity_contract_accepts_salesforce_values() -> None:
    opportunity = Opportunity(
        id="006000000000001AAA",
        name="Renewal",
        account_id="001000000000001AAA",
        amount=Decimal("10"),
        close_date=date(2027, 6, 30),
        stage_name="Qualification",
    )
    assert opportunity.id == "006000000000001AAA"
