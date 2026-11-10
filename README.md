# Funding Workflow Automation

Automatisation du traitement des demandes de financement : soumission, OCR, extraction, contrôle des pièces, routage, décision (automatique ou humaine) et journal d'audit chaîné.

> **État : semaine 1 (cadrage).** Le dépôt contient les documents de cadrage, les contrats de données (Pydantic) et des fixtures fictives. Aucun pipeline, appel LLM ni logique métier n'est encore implémenté.

## Lancer les tests

Prérequis : Python 3.11 ou plus récent.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
python tools/gen_fixtures.py --check   # vérifie que les fixtures correspondent au générateur
```

`pytest` est configuré dans `pyproject.toml`, avec `packages/` ajouté au chemin d'import (le paquet s'importe sous le nom `core`). Les tests vérifient :
- `tests/test_models_serialization.py` : la sérialisation JSON aller-retour de chaque modèle et les invariants (droits agent/humain, règle du premier événement d'audit, refus des flottants dans le payload, etc.) ;
- `tests/test_fixtures.py` : chaque fixture se charge, est marquée fictive, référence une décision de routage valide (`simple`, `sensitive` ou `null`) et respecte les bornes des règles. Les fixtures-questions sont seulement chargées, sans assertion de routage ;
- `tests/test_audit_chain_vectors.py` : les deux vecteurs SHA-256 de `docs/audit-chain.md`, reconstruits à partir des champs.

## Où trouver quoi

| Chemin | Contenu |
|---|---|
| [docs/glossary.md](docs/glossary.md) | **Vocabulaire commun** : statuts, types et enums (source unique) |
| [docs/scope.md](docs/scope.md) | Périmètre du MVP de 6 semaines, avec ce qui est hors MVP et pourquoi |
| [docs/routing-rules.md](docs/routing-rules.md) | Règles de routage R1 à R7 et R9 (simple / sensible / attente), bornes exactes |
| [docs/data-contracts.md](docs/data-contracts.md) | Description des modèles `Client`, `Piece`, `Decision`, `Dossier` et `AuditEvent` |
| [docs/audit-chain.md](docs/audit-chain.md) | Spécification de la chaîne de hash SHA-256, avec un exemple de référence |
| [docs/open-questions.md](docs/open-questions.md) | Décisions métier non validées : Q1 à Q10 provisoires, Q11 à Q18 à trancher |
| [packages/core/models.py](packages/core/models.py) | Modèles Pydantic v2 et paramètres de cadrage |
| [fixtures/dossiers/](fixtures/dossiers/) | 23 dossiers de test **fictifs**, liste sensible fictive et description du format |
| [fixtures/open-questions/](fixtures/open-questions/) | Fixtures-questions sans routage attendu (Q12) |
| [tools/](tools/) | `gen_fixtures.py` : générateur des fixtures, avec un mode `--check` |
| [tests/](tests/) | Tests unitaires |

## Règles du dépôt

- **Données fictives uniquement.** Aucune donnée réelle ni dérivée de personnes réelles (voir `fixtures/dossiers/README.md`).
- Documentation et commentaires en français, noms de code en anglais.
- Toute décision métier ambiguë va dans `docs/open-questions.md` avant d'être codée.
- Pour changer le vocabulaire, on modifie d'abord `docs/glossary.md`, puis le code et les autres documents.
