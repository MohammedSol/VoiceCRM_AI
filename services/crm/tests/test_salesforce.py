"""Salesforce adapter tests; all HTTP traffic is intercepted by respx."""

import json
from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx

from app.errors import CrmAuthenticationError
from app.models import OpportunityDraft
from app.salesforce import SalesforceCrm, SalesforceSettings, _escape_like


@pytest.fixture
def settings() -> SalesforceSettings:
    return SalesforceSettings(
        client_id="test-client",
        client_secret="test-secret",
    )


def test_soql_search_term_escapes_quotes_and_like_wildcards() -> None:
    assert _escape_like("Atlas' OR Name != '%'_") == r"Atlas\' OR Name != \'\%\'\_"


@pytest.mark.asyncio
async def test_search_accounts_authenticates_and_sends_escaped_soql(
    settings: SalesforceSettings,
) -> None:
    with respx.mock(assert_all_called=True) as router:
        router.post("https://login.salesforce.com/services/oauth2/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "test-token",
                    "instance_url": "https://example.my.salesforce.com",
                },
            )
        )
        query_route = router.get(
            "https://example.my.salesforce.com/services/data/v60.0/query"
        ).mock(
            return_value=httpx.Response(
                200,
                json={"records": [{"Id": "001000000000001AAA", "Name": "Atlas"}]},
            )
        )
        async with SalesforceCrm(settings) as crm:
            accounts = await crm.search_accounts("Atlas' OR Name != '%")

    assert [account.name for account in accounts] == ["Atlas"]
    assert query_route.calls.call_count == 1
    sent_soql = query_route.calls.last.request.url.params["q"]
    assert r"Atlas\' OR Name != \'\%" in sent_soql
    assert (
        query_route.calls.last.request.headers["Authorization"] == "Bearer test-token"
    )


@pytest.mark.asyncio
async def test_expired_token_is_refreshed_once(settings: SalesforceSettings) -> None:
    token_count = 0
    request_count = 0

    def issue_token(_: httpx.Request) -> httpx.Response:
        nonlocal token_count
        token_count += 1
        return httpx.Response(
            200,
            json={
                "access_token": f"token-{token_count}",
                "instance_url": "https://example.my.salesforce.com",
            },
        )

    def query(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(401)
        return httpx.Response(200, json={"records": []})

    with respx.mock(assert_all_called=True) as router:
        router.post("https://login.salesforce.com/services/oauth2/token").mock(
            side_effect=issue_token
        )
        query_route = router.get(
            "https://example.my.salesforce.com/services/data/v60.0/query"
        ).mock(side_effect=query)
        async with SalesforceCrm(settings) as crm:
            assert await crm.search_accounts("Atlas") == []

    assert token_count == 2
    assert query_route.calls.call_count == 2


@pytest.mark.asyncio
async def test_create_opportunity_maps_payload_and_returns_record_id(
    settings: SalesforceSettings,
) -> None:
    with respx.mock(assert_all_called=True) as router:
        router.post("https://login.salesforce.com/services/oauth2/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "test-token",
                    "instance_url": "https://example.my.salesforce.com",
                },
            )
        )
        create_route = router.post(
            "https://example.my.salesforce.com/services/data/v60.0/sobjects/Opportunity"
        ).mock(
            return_value=httpx.Response(
                201, json={"id": "006000000000001AAA", "success": True}
            )
        )
        async with SalesforceCrm(settings) as crm:
            record_id = await crm.create_opportunity(
                OpportunityDraft(
                    name="Renewal",
                    account_id="001000000000001AAA",
                    amount=Decimal("2500.75"),
                    close_date=date(2027, 6, 30),
                    stage_name="Qualification",
                )
            )

    assert record_id == "006000000000001AAA"
    assert json.loads(create_route.calls.last.request.content) == {
        "Name": "Renewal",
        "AccountId": "001000000000001AAA",
        "Amount": 2500.75,
        "CloseDate": "2027-06-30",
        "StageName": "Qualification",
    }


@pytest.mark.asyncio
async def test_oauth_failure_does_not_expose_credentials(
    settings: SalesforceSettings,
) -> None:
    with respx.mock(assert_all_called=True) as router:
        router.post("https://login.salesforce.com/services/oauth2/token").mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": "invalid_client",
                    "error_description": "Rejected test-secret for test-client",
                },
            )
        )
        async with SalesforceCrm(settings) as crm:
            with pytest.raises(CrmAuthenticationError) as error:
                await crm.search_accounts("Atlas")

    assert "invalid_client" in str(error.value)
    assert "test-secret" not in str(error.value)
    assert "test-client" not in str(error.value)
