# ADR-003 — Make absent sur Windows : scripts PowerShell équivalents

**Date :** 2026-11-18
**Statut :** Accepté
**Auteur :** Mohammed Solimani (Sprint 0)

## Contexte

Le plan demande un Makefile avec `make up`, `make down`, `make test`, `make lint`.
La machine de développement tourne sous Windows 11, et `make` n'est pas disponible
(`where.exe make` retourne vide).

## Décision

**Conserver le Makefile** pour la CI GitHub Actions (runners Ubuntu) **et** créer des
scripts PowerShell équivalents dans `scripts/` pour les développeurs Windows.

| Cible make  | Script PowerShell       |
|-------------|------------------------|
| `make up`   | `scripts/up.ps1`       |
| `make down` | `scripts/down.ps1`     |
| `make test` | `scripts/test.ps1`     |
| `make lint` | `scripts/lint.ps1`     |

## Raisons

1. **CI** : les runners GitHub Actions sont Ubuntu → `make` fonctionne en CI.
2. **Windows** : `winget install GnuWin32.Make` ou WSL seraient des prérequis supplémentaires
   à documenter ; les scripts PowerShell sont natifs Windows 11.
3. **Plan** : « Si `make` est absent, propose des scripts PowerShell équivalents dans
   `scripts/` en gardant le Makefile pour la CI. » — c'est exactement la consigne.

## Conséquences

- Les développeurs Windows lancent `.\scripts\test.ps1` au lieu de `make test`.
- Le README documente les deux variantes.
- Si un membre installe `make` via Chocolatey ou WSL, le Makefile fonctionne directement.
