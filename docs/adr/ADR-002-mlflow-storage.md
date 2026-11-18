# ADR-002 — Stockage MLflow : fichiers locaux (option la plus simple)

**Date :** 2026-11-18
**Statut :** Accepté
**Auteur :** Mohammed Solimani (Sprint 0)

## Contexte

Le plan mentionne MLflow pour le suivi des évaluations (Sprint 8). Le Sprint 0 demande
de lancer MLflow dans docker-compose. MLflow supporte plusieurs backends de stockage :
PostgreSQL, MySQL, SQLite, et système de fichiers local.

## Décision

**Stockage par fichiers locaux** : `--backend-store-uri /mlflow/mlruns`.
Un volume Docker nommé (`mlflow_data`) persiste les données entre les redémarrages.

## Raisons

1. **Contrainte du plan** : « prends l'option la plus simple qui fonctionne ».
2. **Sprint 0** : MLflow sert uniquement à vérifier que le conteneur démarre healthy.
   Les vrais runs commencent au Sprint 3.
3. **Zéro dépendance supplémentaire** : pas de base dédiée pour MLflow, pas de configuration
   SQLAlchemy supplémentaire.
4. **Réversibilité** : migrer vers PostgreSQL-backend au Sprint 3 est trivial (changer
   `--backend-store-uri`, même volume Docker pour les artefacts).

## Conséquences

- Les métadonnées MLflow ne sont pas interrogeables par SQL directement.
- En cas de perte du volume `mlflow_data`, l'historique des runs est perdu
  (acceptable en développement).
- Si l'équipe veut requêtes SQL sur les runs au Sprint 8, changer le backend store
  vers PostgreSQL (un seul paramètre).

## Alternatives rejetées

- **PostgreSQL comme backend MLflow** : surcharge de config pour Sprint 0 ; à reconsidérer
  si nécessaire au Sprint 3.
