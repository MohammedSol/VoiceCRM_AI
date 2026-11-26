"""Salesforce read/update and provider-error behavior."""

import json
from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx

from app.errors import CrmAuthenticationError, CrmNotFoundError, CrmRequestError
from app.salesforce import SalesforceCrm, SalesforceSettings


@pytest.fixture
def settings() -> SalesforceSettings:
    return SalesforceSettings(client_id="client", client_secret="secret")


def add_token_route(router: respx.MockRouter) -> None:
    router.post("https://login.salesforce.com/services/oauth2/token").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "token",
                "instance_url": "https://example.my.salesforce.com",
            },
        )
    )


@pytest.mark.asyncio
async def test_search_opportunities_parses_account_and_optional_fields(
    settings: SalesforceSettings,
) -> None:
    with respx.mock(assert_all_called=True) as router:
        add_token_route(router)
        router.get("https://example.my.salesforce.com/services/data/v60.0/query").mock(
            return_value=httpx.Response(
                200,
                json={
                    "records": [
                        {
                            "Id": "006000000000001AAA",
                            "Name": "Renewal",
                            "AccountId": "001000000000001AAA",
                            "Account": {"Name": "Atlas"},
                            "Amount": 1200.50,
                            "CloseDate": "2027-06-30",
                            "StageName": "Qualification",
                        }
                    ]
                },
            )
        )
        async with SalesforceCrm(settings) as crm:
            result = await crm.search_opportunities("Atlas")

    assert len(result) == 1
    assert result[0].account_name == "Atlas"
    assert result[0].amount == Decimal("1200.5")
    assert result[0].close_date == date(2027, 6, 30)


@pytest.mark.asyncio
async def test_get_opportunity_validates_id_and_maps_not_found(
    settings: SalesforceSettings,
) -> None:
    with pytest.raises(ValueError, match="record ID"):
        async with SalesforceCrm(settings) as crm:
            await crm.get_opportunity("invalid/id")

    with respx.mock(assert_all_called=True) as router:
        add_token_route(router)
        router.get("https://example.my.salesforce.com/services/data/v60.0/query").mock(
            return_value=httpx.Response(200, json={"records": []})
        )
        async with SalesforceCrm(settings) as crm:
            with pytest.raises(CrmNotFoundError):
                await crm.get_opportunity("006000000000001AAA")


@pytest.mark.asyncio
async def test_update_opportunity_uses_salesforce_field_names_and_patch(
    settings: SalesforceSettings,
) -> None:
    with respx.mock(assert_all_called=True) as router:
        add_token_route(router)
        update_route = router.patch(
            "https://example.my.salesforce.com/services/data/v60.0/"
            "sobjects/Opportunity/006000000000001AAA"
        ).mock(return_value=httpx.Response(204))
        async with SalesforceCrm(settings) as crm:
            await crm.update_opportunity(
                "006000000000001AAA",
                {"amount": Decimal("500"), "close_date": date(2027, 7, 1)},
            )

    assert json.loads(update_route.calls.last.request.content) == {
        "Amount": 500.0,
        "CloseDate": "2027-07-01",
    }


@pytest.mark.asyncio
async def test_update_rejects_fields_outside_the_allowed_list(
    settings: SalesforceSettings,
) -> None:
    async with SalesforceCrm(settings) as crm:
        with pytest.raises(ValueError, match="Unsupported"):
            await crm.update_opportunity(
                "006000000000001AAA", {"owner_id": "005000000000001AAA"}
            )


@pytest.mark.parametrize(
    ("status_code", "expected_exception"),
    [
        (403, CrmAuthenticationError),
        (500, CrmRequestError),
    ],
)
@pytest.mark.asyncio
async def test_salesforce_http_errors_are_mapped_without_response_body(
    settings: SalesforceSettings,
    status_code: int,
    expected_exception: type[Exception],
) -> None:
    with respx.mock(assert_all_called=True) as router:
        add_token_route(router)
        router.get("https://example.my.salesforce.com/services/data/v60.0/query").mock(
            return_value=httpx.Response(status_code, text="private response")
        )
        async with SalesforceCrm(settings) as crm:
            with pytest.raises(expected_exception) as error:
                await crm.search_accounts("Atlas")

    assert "private response" not in str(error.value)
