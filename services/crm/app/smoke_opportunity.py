"""Explicitly confirmed Salesforce opportunity create/read smoke test."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.errors import CrmError, CrmRequestError
from app.models import OpportunityDraft
from app.salesforce import SalesforceCrm, SalesforceSettings


async def run_smoke(
    account_name: str,
    amount: Decimal,
    close_date: date,
    stage_name: str,
) -> int:
    """Create one clearly labelled test opportunity after explicit confirmation."""
    try:
        settings = SalesforceSettings.from_env()
        async with SalesforceCrm(settings) as crm:
            matches = await crm.search_accounts(account_name)
            exact_matches = [
                item
                for item in matches
                if item.name.casefold() == account_name.casefold()
            ]
            if len(exact_matches) != 1:
                print(
                    "Il faut exactement un compte dont le nom correspond. "
                    f"Correspondances exactes : {len(exact_matches)}.",
                    file=sys.stderr,
                )
                return 2

            account = exact_matches[0]
            unique_suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
            opportunity_name = f"CRM Sprint 1 smoke {unique_suffix}"
            print("Une opportunité de test va être créée dans Salesforce :")
            print(f"  Compte : {account.name}")
            print(f"  Opportunité : {opportunity_name}")
            print(f"  Montant : {amount}")
            print(f"  Clôture : {close_date.isoformat()}")
            print(f"  Étape : {stage_name}")
            if input("Pour confirmer l’écriture, tape CREATE : ") != "CREATE":
                print("Test annulé ; aucune opportunité n'a été créée.")
                return 3

            draft = OpportunityDraft(
                name=opportunity_name,
                account_id=account.id,
                amount=amount,
                close_date=close_date,
                stage_name=stage_name,
            )
            opportunity_id = await crm.create_opportunity(draft)
            saved = await crm.get_opportunity(opportunity_id)
            if (
                saved.name != opportunity_name
                or saved.account_id != account.id
                or saved.stage_name != stage_name
            ):
                raise CrmRequestError(
                    "L'opportunité a été créée, mais la relecture ne correspond pas"
                )
    except (CrmError, ValueError, InvalidOperation) as exc:
        print(f"Test de création/relecture échoué : {exc}", file=sys.stderr)
        return 1

    print(
        "Succès : opportunité créée puis relue. "
        f"Identifiant Salesforce : {opportunity_id}"
    )
    return 0


def _positive_amount(value: str) -> Decimal:
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("Le montant doit être un nombre") from exc
    if not amount.is_finite() or amount <= 0:
        raise argparse.ArgumentTypeError("Le montant doit être supérieur à zéro")
    return amount


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Utilise le format AAAA-MM-JJ") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Crée puis relit une opportunité de test après confirmation explicite."
        )
    )
    parser.add_argument("--account", required=True, help="Nom exact du compte de test")
    parser.add_argument("--amount", type=_positive_amount, default=Decimal("10000"))
    parser.add_argument(
        "--close-date",
        type=_iso_date,
        default=date.today() + timedelta(days=90),
        help="Date future au format AAAA-MM-JJ (défaut : dans 90 jours)",
    )
    parser.add_argument("--stage", default="Qualification")
    args = parser.parse_args()
    return asyncio.run(
        run_smoke(args.account, args.amount, args.close_date, args.stage)
    )


if __name__ == "__main__":
    raise SystemExit(main())
