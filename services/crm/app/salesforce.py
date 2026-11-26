"""Salesforce REST adapter using OAuth 2.0 client-credentials flow."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from app.errors import (
    CrmAuthenticationError,
    CrmNotFoundError,
    CrmRequestError,
)
from app.models import Account, Opportunity, OpportunityDraft


@dataclass(frozen=True)
class SalesforceSettings:
    """Non-secret Salesforce connection configuration."""

    client_id: str
    client_secret: str
    login_url: str = "https://login.salesforce.com"
    api_version: str = "v60.0"
    timeout_seconds: float = 15.0

    @classmethod
    def from_env(cls) -> SalesforceSettings:
        client_id = os.getenv("SALESFORCE_CLIENT_ID", "")
        client_secret = os.getenv("SALESFORCE_CLIENT_SECRET", "")
        login_url = os.getenv("SALESFORCE_LOGIN_URL", "").rstrip("/")
        if not client_id or not client_secret:
            raise ValueError("Salesforce OAuth client credentials are required")
        if not login_url:
            raise ValueError(
                "SALESFORCE_LOGIN_URL must be set to your Salesforce My Domain URL"
            )
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            login_url=login_url,
            api_version=os.getenv("SALESFORCE_API_VERSION", "v60.0"),
        )

    def __post_init__(self) -> None:
        parsed = urlparse(self.login_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Salesforce login URL must use HTTPS")
        if not re.fullmatch(r"v\d+\.0", self.api_version):
            raise ValueError("Salesforce API version must look like 'v60.0'")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class SalesforceCrm:
    """Salesforce implementation of the opportunity CRM port.

    Accept an injected AsyncClient to test without a network or credentials.
    If no client is supplied, this adapter owns and closes its HTTP client.
    """

    def __init__(
        self,
        settings: SalesforceSettings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self._client = client or httpx.AsyncClient(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
        )
        self._owns_client = client is None
        self._access_token: str | None = None
        self._instance_url: str | None = None

    async def __aenter__(self) -> SalesforceCrm:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search_accounts(self, term: str) -> list[Account]:
        soql = (
            "SELECT Id, Name FROM Account "
            f"WHERE Name LIKE '%{_escape_like(term)}%' ORDER BY Name LIMIT 50"
        )
        records = await self._query(soql)
        return [
            Account(id=_required_string(row, "Id"), name=_required_string(row, "Name"))
            for row in records
        ]

    async def search_opportunities(self, term: str) -> list[Opportunity]:
        escaped = _escape_like(term)
        soql = (
            "SELECT Id, Name, AccountId, Account.Name, Amount, CloseDate, StageName "
            "FROM Opportunity WHERE "
            f"Name LIKE '%{escaped}%' OR Account.Name LIKE '%{escaped}%' "
            "ORDER BY Name LIMIT 50"
        )
        return [_parse_opportunity(row) for row in await self._query(soql)]

    async def create_opportunity(self, draft: OpportunityDraft) -> str:
        payload = {
            "Name": draft.name,
            "AccountId": draft.account_id,
            "Amount": float(draft.amount),
            "CloseDate": draft.close_date.isoformat(),
            "StageName": draft.stage_name,
        }
        response = await self._request("POST", "/sobjects/Opportunity", json=payload)
        try:
            data = response.json()
        except ValueError as exc:
            raise CrmRequestError(
                "Salesforce returned an invalid create response"
            ) from exc
        record_id = data.get("id") if isinstance(data, dict) else None
        if response.status_code not in (200, 201) or not isinstance(record_id, str):
            raise CrmRequestError("Salesforce did not confirm opportunity creation")
        return record_id

    async def get_opportunity(self, opportunity_id: str) -> Opportunity:
        _validate_record_id(opportunity_id)
        soql = (
            "SELECT Id, Name, AccountId, Account.Name, Amount, CloseDate, StageName "
            f"FROM Opportunity WHERE Id = '{opportunity_id}' LIMIT 1"
        )
        records = await self._query(soql)
        if not records:
            raise CrmNotFoundError("Opportunity not found or not accessible")
        return _parse_opportunity(records[0])

    async def update_opportunity(
        self, opportunity_id: str, changes: dict[str, object]
    ) -> None:
        _validate_record_id(opportunity_id)
        field_names = {
            "name": "Name",
            "amount": "Amount",
            "close_date": "CloseDate",
            "stage_name": "StageName",
        }
        unknown = set(changes) - set(field_names)
        if unknown:
            raise ValueError(f"Unsupported opportunity fields: {sorted(unknown)}")
        if not changes:
            raise ValueError("At least one opportunity field must be provided")
        payload: dict[str, object] = {}
        for key, value in changes.items():
            if key == "amount" and isinstance(value, Decimal):
                value = float(value)
            elif key == "close_date" and isinstance(value, date):
                value = value.isoformat()
            payload[field_names[key]] = value
        path_id = quote(opportunity_id, safe="")
        response = await self._request(
            "PATCH", f"/sobjects/Opportunity/{path_id}", json=payload
        )
        if response.status_code not in (200, 204):
            raise CrmRequestError("Salesforce did not confirm opportunity update")

    async def _query(self, soql: str) -> list[dict[str, Any]]:
        response = await self._request(
            "GET",
            "/query",
            params={"q": soql},
        )
        try:
            data = response.json()
        except ValueError as exc:
            raise CrmRequestError(
                "Salesforce returned an invalid query response"
            ) from exc
        records = data.get("records") if isinstance(data, dict) else None
        if response.status_code != 200 or not isinstance(records, list):
            raise CrmRequestError("Salesforce query failed")
        if not all(isinstance(row, dict) for row in records):
            raise CrmRequestError("Salesforce returned malformed query records")
        return records

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(2):
            await self._ensure_token()
            assert self._access_token is not None
            assert self._instance_url is not None
            url = (
                f"{self._instance_url}/services/data/{self.settings.api_version}{path}"
            )
            try:
                response = await self._client.request(
                    method,
                    url,
                    headers={"Authorization": f"Bearer {self._access_token}"},
                    **kwargs,
                )
            except httpx.HTTPError as exc:
                raise CrmRequestError(
                    "Salesforce request failed due to a network error"
                ) from exc
            if response.status_code == 401 and attempt == 0:
                self._access_token = None
                continue
            if response.status_code == 404:
                raise CrmNotFoundError(
                    "Salesforce record was not found or is not accessible"
                )
            if response.status_code == 401:
                raise CrmAuthenticationError("Salesforce rejected the access token")
            if response.status_code == 403:
                raise CrmAuthenticationError(
                    "Salesforce integration user lacks permission"
                )
            if response.status_code >= 400:
                raise CrmRequestError(
                    f"Salesforce request failed with HTTP {response.status_code}"
                )
            return response
        raise CrmAuthenticationError("Salesforce authentication retry was exhausted")

    async def _ensure_token(self) -> None:
        if self._access_token is not None and self._instance_url is not None:
            return
        token_url = f"{self.settings.login_url}/services/oauth2/token"
        try:
            response = await self._client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.client_id,
                    "client_secret": self.settings.client_secret,
                },
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise CrmAuthenticationError("Salesforce OAuth request failed") from exc
        if response.status_code != 200:
            detail = _safe_oauth_error(response, self.settings)
            suffix = f" ({detail})" if detail else ""
            raise CrmAuthenticationError(
                f"Salesforce OAuth failed with HTTP {response.status_code}{suffix}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise CrmAuthenticationError(
                "Salesforce OAuth response was invalid"
            ) from exc
        token = data.get("access_token") if isinstance(data, dict) else None
        instance_url = data.get("instance_url") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token or not isinstance(instance_url, str):
            raise CrmAuthenticationError("Salesforce OAuth response was incomplete")
        parsed = urlparse(instance_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise CrmAuthenticationError("Salesforce returned an invalid instance URL")
        self._access_token = token
        self._instance_url = instance_url.rstrip("/")


def _safe_oauth_error(response: httpx.Response, settings: SalesforceSettings) -> str:
    """Return a short OAuth error code/message without echoing configured secrets."""
    try:
        data = response.json()
    except ValueError:
        return ""
    if not isinstance(data, dict):
        return ""

    parts: list[str] = []
    for key in ("error", "error_description"):
        value = data.get(key)
        if isinstance(value, str) and value:
            safe_value = value
            for credential in (settings.client_secret, settings.client_id):
                if credential:
                    safe_value = safe_value.replace(credential, "[redacted]")
            safe_value = re.sub(r"[\x00-\x1f\x7f]+", " ", safe_value)
            parts.append(safe_value[:200])
    return ": ".join(parts)


def _escape_like(value: str) -> str:
    """Escape user text before embedding it in a SOQL LIKE string literal."""
    return (
        value.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _required_string(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise CrmRequestError(f"Salesforce record is missing required field {key}")
    return value


def _parse_opportunity(record: dict[str, Any]) -> Opportunity:
    close_date_value = record.get("CloseDate")
    amount_value = record.get("Amount")
    account = record.get("Account")
    account_name = account.get("Name") if isinstance(account, dict) else None
    try:
        return Opportunity(
            id=_required_string(record, "Id"),
            name=_required_string(record, "Name"),
            account_id=record.get("AccountId"),
            account_name=account_name,
            amount=Decimal(str(amount_value)) if amount_value is not None else None,
            close_date=date.fromisoformat(close_date_value)
            if isinstance(close_date_value, str)
            else None,
            stage_name=_required_string(record, "StageName"),
        )
    except (ValueError, ArithmeticError) as exc:
        raise CrmRequestError("Salesforce returned invalid opportunity fields") from exc


def _validate_record_id(record_id: str) -> None:
    if not re.fullmatch(r"[a-zA-Z0-9]{15,18}", record_id):
        raise ValueError(
            "Salesforce record ID must be 15 or 18 alphanumeric characters"
        )
