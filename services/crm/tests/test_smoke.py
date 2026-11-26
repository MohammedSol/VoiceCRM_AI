"""Tests for the read-only Salesforce connectivity command."""

from __future__ import annotations

import pytest

from app import smoke
from app.models import Account
from app.salesforce import SalesforceSettings


class StubCrm:
    def __init__(self, _: SalesforceSettings) -> None:
        pass

    async def __aenter__(self) -> StubCrm:
        return self

    async def __aexit__(self, *_: object) -> None:
        pass

    async def search_accounts(self, _: str) -> list[Account]:
        return [Account(id="001000000000001AAA", name="Private Account Name")]


@pytest.mark.asyncio
async def test_smoke_reports_success_without_printing_account_data(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        smoke.SalesforceSettings,
        "from_env",
        classmethod(
            lambda cls: SalesforceSettings(client_id="id", client_secret="secret")
        ),
    )
    monkeypatch.setattr(smoke, "SalesforceCrm", StubCrm)

    result = await smoke.run_smoke("Atlas")
    output = capsys.readouterr()

    assert result == 0
    assert "Connexion Salesforce réussie" in output.out
    assert "1 compte(s) trouvé(s)" in output.out
    assert "Private Account Name" not in output.out
    assert "secret" not in output.out


@pytest.mark.asyncio
async def test_smoke_rejects_empty_search_term(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = await smoke.run_smoke("   ")
    output = capsys.readouterr()

    assert result == 2
    assert "ne peut pas être vide" in output.err
