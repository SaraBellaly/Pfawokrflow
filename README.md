# Funding Workflow Automation

Automatisation du traitement des demandes de financement : soumission, OCR, extraction, contrôle des pièces, routage, décision (automatique ou humaine) et journal d'audit chaîné.

> **État : semaine 2 (socle technique).** Le monorepo contient les contrats de données, les fixtures, l'infrastructure Docker (FastAPI, PostgreSQL + pgvector, Redis, Celery), les migrations Alembic et la table d'audit append-only. Le modèle LLM sera en cloud (fournisseur à choisir). Aucune logique métier n'est encore implémentée.

## Démarrage rapide

### Tests unitaires (sans Docker)

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
python tools/gen_fixtures.py --check
```

### Infrastructure complète (Docker)

```bash
docker compose up --build
```

Services lancés :
- **API** : http://localhost:8000 (FastAPI, healthcheck sur `/health`)
- **PostgreSQL** : localhost:5432 (avec pgvector)
- **Redis** : localhost:6379
- **Worker Celery** : traitement asynchrone (OCR, extraction)

### Migrations

```bash
# Depuis le conteneur api ou en local avec DATABASE_URL_SYNC configuré
alembic upgrade head
```

## Tests

`pytest` est configuré dans `pyproject.toml`, avec `packages/` ajouté au chemin d'import. Les tests vérifient :
- `tests/test_models_serialization.py` : sérialisation JSON aller-retour et invariants des modèles Pydantic ;
- `tests/test_fixtures.py` : chargement, marquage fictif, routage et bornes des fixtures ;
- `tests/test_audit_chain_vectors.py` : les deux vecteurs SHA-256 de `docs/audit-chain.md` ;
- `tests/test_audit_hash.py` : `compute_audit_hash` reproduit exactement les vecteurs de référence ;
- `tests/test_infra_imports.py` : import des modules DB, API et config sans erreur.

## Où trouver quoi

| Chemin | Contenu |
|---|---|
| [docs/](docs/) | Cadrage : glossaire, périmètre, routage, contrats de données, chaîne d'audit, questions ouvertes |
| [packages/core/models.py](packages/core/models.py) | Modèles Pydantic v2 et paramètres de cadrage |
| [packages/db/](packages/db/) | Couche base de données : modèles SQLAlchemy, engine async, calcul de hash d'audit |
| [packages/api/](packages/api/) | Application FastAPI (config, routeurs, healthcheck) |
| [packages/worker/](packages/worker/) | Worker Celery (tâches OCR et extraction, stubs) |
| [alembic/](alembic/) | Migrations : schéma initial + table d'audit append-only avec triggers |
| [fixtures/dossiers/](fixtures/dossiers/) | 23 dossiers de test **fictifs** |
| [fixtures/open-questions/](fixtures/open-questions/) | Fixtures-questions sans routage attendu |
| [tools/](tools/) | `gen_fixtures.py` : générateur des fixtures |
| [tests/](tests/) | Tests unitaires |
| [docker-compose.yml](docker-compose.yml) | Orchestration des services |

## Règles du dépôt

- **Données fictives uniquement.** Aucune donnée réelle ni dérivée de personnes réelles (voir `fixtures/dossiers/README.md`).
- Documentation et commentaires en français, noms de code en anglais.
- Toute décision métier ambiguë va dans `docs/open-questions.md` avant d'être codée.
- Pour changer le vocabulaire, on modifie d'abord `docs/glossary.md`, puis le code et les autres documents.