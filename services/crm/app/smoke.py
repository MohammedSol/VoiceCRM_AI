"""Read-only live connectivity check for a Salesforce Developer Edition."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.errors import CrmError
from app.salesforce import SalesforceCrm, SalesforceSettings


async def run_smoke(term: str) -> int:
    """Authenticate and run a read-only account search without printing records."""
    if not term.strip():
        print("Le terme de recherche ne peut pas être vide.", file=sys.stderr)
        return 2

    try:
        settings = SalesforceSettings.from_env()
        async with SalesforceCrm(settings) as crm:
            matches = await crm.search_accounts(term)
    except (CrmError, ValueError) as exc:
        print(f"Connexion Salesforce échouée : {exc}", file=sys.stderr)
        return 1

    print(f"Connexion Salesforce réussie. {len(matches)} compte(s) trouvé(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Vérifie la connexion Salesforce avec une recherche en lecture seule."
        )
    )
    parser.add_argument(
        "--term",
        required=True,
        help="Texte à rechercher dans les noms de comptes (ne pas fournir de secret).",
    )
    args = parser.parse_args()
    return asyncio.run(run_smoke(args.term))


if __name__ == "__main__":
    raise SystemExit(main())
