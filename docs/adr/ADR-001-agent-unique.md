# ADR-001 — Agent unique LangGraph (confirmé par le prof)

**Date :** 2026-11-18
**Statut :** Accepté
**Auteur :** Mohammed Solimani (Sprint 0)

## Contexte

Le projet nécessite de comprendre des phrases en langage naturel et d'appeler des outils
(CRM Salesforce). Plusieurs architectures d'agents sont possibles : agent unique, hiérarchie
multi-agents, pipeline fixe.

## Décision

**Un seul agent LangGraph**, sous forme de graphe d'états, avec au maximum six outils.

Le prof a confirmé cette architecture lors de la présentation du projet.

## Raisons

1. **Simplicité** : un seul graphe, un seul prompt système, une seule fabrique de modèle.
   Moins de surface d'erreur, plus facile à tester et à déboguer.
2. **Latence** : un seul appel LLM par tour (hors boucle d'outils). Un multi-agent aurait
   plusieurs appels LLM en cascade, inaccessible sur CPU avec un modèle local.
3. **Contrôle** : la validation déterministe (`packages/validation`) est la seule porte vers
   Salesforce — l'agent ne peut pas contourner. Un orchestrateur multi-agents rendrait ce
   contrôle plus difficile à garantir.
4. **Plan du projet** : « Garder un seul nœud de décision, pas de sous-agents »
   (Stack technique, colonne point d'attention).

## Conséquences

- L'agent doit gérer lui-même tous les cas d'ambiguïté (compte inexistant, plusieurs candidats,
  champs manquants) via les branches du graphe — cf. Sprint 4.
- Si le modèle choisi (Qwen3.5-4B) est insuffisant pour enchaîner correctement les six outils,
  plan B : modèle plus grand via la fabrique `llm.py`, sans changer l'architecture.
- Cette décision est réversible avant le Sprint 3 si les mesures indiquent un besoin réel
  de sous-agents.

## Alternatives rejetées

- **Multi-agents** : latence trop élevée sur CPU, complexité disproportionnée au périmètre.
- **Pipeline fixe** : trop rigide pour gérer les ambiguïtés conversationnelles.
