# Sprint 1 — Connecteur CRM

Le package expose un contrat asynchrone `CrmPort`, une implémentation `FakeCrm` en mémoire
pour les tests/démos hors ligne et un adaptateur `SalesforceCrm` utilisant l'API REST.
L'authentification réelle utilise OAuth 2.0 **Client Credentials**. Il faut activer ce flux
sur une application Salesforce de test et attribuer à l'utilisateur d'intégration des
permissions minimales sur Account et Opportunity. Certaines organisations nécessitent une
configuration différente ; ne jamais utiliser les identifiants de production pour les tests.

## Configuration Salesforce

Ajouter ces variables à l'environnement (ou au `.env` local non versionné) :

```text
SALESFORCE_CLIENT_ID=...
SALESFORCE_CLIENT_SECRET=...
SALESFORCE_LOGIN_URL=https://<ton-domaine-my-salesforce>
SALESFORCE_API_VERSION=v60.0
```

Pour le flux **Client Credentials**, utilise le domaine My Domain de ton organisation
(comme son URL `...my.salesforce.com`), sans chemin supplémentaire. N'utilise pas
`login.salesforce.com` ni l'URL `test.salesforce.com` pour ce flux. Le connecteur récupère
l'`instance_url` depuis la réponse OAuth et ne journalise pas les identifiants. Ne jamais
committer `.env` ou les secrets Salesforce.

## Vérifier la connexion réelle (lecture seule)

Depuis la racine du dépôt, dans PowerShell :

```powershell
Set-Location services/crm
uv run --env-file ../../.env python -m app.smoke --term "Atlas"
```

Remplace `Atlas` par le début du nom d'un compte de test présent dans ton organisation.
La commande recherche uniquement des comptes et affiche le nombre de résultats, pas les
noms ni les identifiants. Elle ne crée et ne modifie aucun enregistrement. Un succès
confirme OAuth et l'accès en lecture à Account ; le test ne vérifie pas encore les droits
d'écriture sur Opportunity.

## Tester la création puis la relecture d'une opportunité

Cette commande écrit réellement une opportunité dans l'organisation configurée. Utilise
uniquement la Developer Edition de test. Elle demande de taper `CREATE` avant toute écriture,
cherche d'abord un compte au nom exact, puis relit l'opportunité créée. Le nom du test est
unique ; supprime l'enregistrement dans Salesforce après validation si tu le souhaites.

```powershell
Set-Location services/crm
uv run --env-file ../../.env python -m app.smoke_opportunity `
  --account "Acme Test" --amount 10000 --stage "Qualification"
```

La date de clôture est fixée automatiquement à 90 jours dans le futur. `Qualification` est
une valeur active observée dans l'organisation de test ; remplace-la si elle change.

## Exemple local

```python
import asyncio
from app.salesforce import SalesforceCrm, SalesforceSettings

async def main() -> None:
    async with SalesforceCrm(SalesforceSettings.from_env()) as crm:
        for account in await crm.search_accounts("Atlas"):
            print(account.id, account.name)

asyncio.run(main())
```

`FakeCrm` expose les mêmes opérations pour exécuter les tests sans réseau ni compte
Salesforce. Les écritures Salesforce réelles sont limitées à l'organisation de test et
à appeler explicitement par le code client.

## Tests

```powershell
Set-Location services/crm
uv sync --group dev
uv run pytest -v
```
